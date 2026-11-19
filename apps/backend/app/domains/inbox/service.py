"""Inbox service: intake, sending, assignment, handoff (CRM-005…008, 012).

Inbound: channel webhook → identity resolution (phone in the text joins an existing customer) →
conversation → message (deduped on the channel's message id) → ``inbox.message_received`` → Sales
Agent (agent.py), asynchronously.

Outbound: every reply (seller or AI) is stored first as ``queued`` and sent by a worker via the channel
adapter with an idempotency key, so a retry never double-sends and a failure is visible, not lost.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.automation.policy import log_action
from app.domains.channels.models import ChannelConnection, WebhookEvent
from app.domains.customers import service as customers
from app.domains.customers.models import Customer
from app.domains.inbox.models import Conversation, Message, OrderDraft
from app.domains.integrations.base import ChannelCapability, IntegrationError
from app.domains.merchants.models import Membership, Merchant
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
FIRST_RESPONSE_SLA = timedelta(hours=1)
MAX_SEND_ATTEMPTS = 6


def get_conversation(
    db: Session, ctx: TenantContext, conversation_id: uuid.UUID, *, lock: bool = False
) -> Conversation:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    if lock:
        stmt = stmt.with_for_update()
    c = db.scalar(stmt)
    if c is None or c.merchant_id != ctx.merchant_id:
        raise NotFound(code="conversation_not_found")
    return c


# ----------------------------------------------------------------------------- intake
def receive(db: Session, connection: ChannelConnection, raw: dict[str, Any]) -> Message | None:
    from app.domains.channels.service import adapter_for
    from app.domains.inbox.extract import understand

    m = adapter_for(connection).normalize_message(raw)
    if m is None:
        return None
    merchant_id = connection.merchant_id
    bind_tenant(db, merchant_id)
    hints = understand(m.text)
    cust = customers.resolve_identity(
        db,
        merchant_id,
        provider=connection.provider,
        external_id=m.sender_id,
        display_name=m.sender_name,
        phone=hints.phone,
    )
    conv = db.scalar(
        select(Conversation)
        .where(Conversation.connection_id == connection.id, Conversation.external_thread_id == m.thread_id)
        .with_for_update()
    )
    now = utcnow()
    if conv is None:
        merchant = db.get(Merchant, merchant_id)
        conv = Conversation(
            merchant_id=merchant_id,
            connection_id=connection.id,
            provider=connection.provider,
            external_thread_id=m.thread_id,
            customer_id=cust.id,
            locale=hints.locale if hints.locale == "ne" else (merchant.default_locale if merchant else "en"),
        )
        db.add(conv)
        db.flush()
    elif conv.customer_id != cust.id:
        conv.customer_id = cust.id  # the identity was merged into another customer
    if hints.phone and cust.phone != hints.phone:
        cust = customers.attach_phone(
            db, TenantContext(merchant_id=merchant_id, actor=Actor.system("inbox")), cust, hints.phone
        )
        conv.customer_id = cust.id
    dup = db.scalar(
        select(Message.id).where(
            Message.conversation_id == conv.id, Message.external_message_id == m.message_id
        )
    )
    if dup is not None:
        return None
    if m.post_ref and conv.content_post_id is None:
        # CNT-014 explicit attribution: the channel told us which post the customer came from.
        from app.domains.content.models import ContentPost

        conv.content_post_id = db.scalar(
            select(ContentPost.id).where(
                ContentPost.connection_id == connection.id, ContentPost.external_id == m.post_ref
            )
        )
    conv.locale = hints.locale  # the language of the latest customer message
    msg = Message(
        merchant_id=merchant_id,
        conversation_id=conv.id,
        direction="in",
        author_type="customer",
        text=m.text,
        status="received",
        external_message_id=m.message_id,
        grounding={
            **({"product_ref": m.product_ref} if m.product_ref else {}),
            **({"post_ref": m.post_ref} if m.post_ref else {}),
        },
    )
    db.add(msg)
    conv.status = "open"
    conv.last_message_at = conv.last_inbound_at = now
    conv.unread_count += 1
    if conv.first_response_due_at is None:
        conv.first_response_due_at = now + FIRST_RESPONSE_SLA
    db.flush()
    outbox.publish(
        db,
        event_type="inbox.message_received",
        aggregate_type="conversation",
        aggregate_id=conv.id,
        merchant_id=merchant_id,
        payload={"conversation_id": str(conv.id), "message_id": str(msg.id)},
    )
    return msg


def _on_message_webhook(db: Session, ev: WebhookEvent) -> None:
    c = db.get(ChannelConnection, ev.connection_id) if ev.connection_id else None
    if c is not None and ChannelCapability.MESSAGES.value in c.capabilities:
        receive(db, c, ev.payload)


def _register() -> None:
    from app.domains.channels.service import webhook_handler

    webhook_handler("message.received")(_on_message_webhook)


_register()


# ----------------------------------------------------------------------------- outbound
def queue_reply(
    db: Session,
    conv: Conversation,
    text: str,
    *,
    author: str,
    user_id: uuid.UUID | None = None,
    intent: str | None = None,
    confidence: float | None = None,
    grounding: dict[str, Any] | None = None,
    send: bool = True,
) -> Message:
    """Store a reply; ``send=False`` keeps it as a suggestion for the seller to approve."""
    text = text.strip()
    if not text:
        raise ValidationFailed("Message is empty", code="message_empty")
    msg = Message(
        merchant_id=conv.merchant_id,
        conversation_id=conv.id,
        direction="out",
        author_type=author,
        author_user_id=user_id,
        text=text[:4000],
        status="queued" if send else "suggested",
        intent=intent,
        confidence=confidence,
        grounding=grounding or {},
    )
    db.add(msg)
    db.flush()
    if send:
        _queue_send(db, msg)
        capability = "customer_notifications" if author == "system" else "customer_messaging"
        performer = {"seller": "user", "ai": "ai", "system": "automation"}.get(author, "system")
        log_action(
            db,
            conv.merchant_id,
            capability,
            "send_message",
            performer,
            key=f"msg:{msg.id}",
            resource_type="conversation",
            resource_id=conv.id,
        )
    return msg


def _queue_send(db: Session, msg: Message, delay: int = 0) -> None:
    conv = db.get(Conversation, msg.conversation_id)
    assert conv is not None
    conv.last_message_at = utcnow()
    conv.first_response_due_at = None
    outbox.publish(
        db,
        event_type="inbox.send_requested",
        aggregate_type="message",
        aggregate_id=msg.id,
        merchant_id=msg.merchant_id,
        payload={"message_id": str(msg.id)},
        delay_seconds=delay,
    )


@handler("inbox.send_requested")
def _send(db: Session, ev: OutboxEvent) -> None:
    from app.domains.channels.service import _mark_expired, adapter_for

    msg = db.scalar(
        select(Message)
        .where(Message.id == uuid.UUID(ev.payload["message_id"]))
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if msg is None or msg.status != "queued":
        return
    bind_tenant(db, msg.merchant_id)
    conv = db.get(Conversation, msg.conversation_id)
    c = db.get(ChannelConnection, conv.connection_id) if conv and conv.connection_id else None
    if conv is None or c is None or c.status != "connected":
        msg.status, msg.error_code = "failed", "reconnect_required"
        return
    try:
        msg.external_message_id = adapter_for(c).send_message(
            conv.external_thread_id, msg.text, idempotency_key=f"msg:{msg.id}"
        )
        msg.status, msg.sent_at, msg.error_code = "sent", utcnow(), None
    except IntegrationError as e:
        msg.error_code = e.code
        if e.auth:
            _mark_expired(db, c, e.code)
            msg.status = "failed"
        elif e.retryable:
            raise  # outbox retries with backoff; the same idempotency key prevents a double send
        else:
            msg.status = "failed"


def send_seller_reply(db: Session, ctx: TenantContext, conversation_id: uuid.UUID, text: str) -> Message:
    conv = get_conversation(db, ctx, conversation_id, lock=True)
    msg = queue_reply(db, conv, text, author="seller", user_id=ctx.actor.id)
    conv.unread_count = 0
    # A human answered: the escalation is handled and the AI steps back until handed back.
    conv.human_handoff, conv.escalated, conv.escalation_reason = True, False, None
    if conv.assigned_user_id is None:
        conv.assigned_user_id = ctx.actor.id
    return msg


def approve_suggestion(db: Session, ctx: TenantContext, message_id: uuid.UUID, text: str | None) -> Message:
    msg = db.get(Message, message_id)
    if msg is None or msg.merchant_id != ctx.merchant_id or msg.status != "suggested":
        raise NotFound(code="suggestion_not_found")
    if text is not None and text.strip() and text.strip() != msg.text:
        msg.grounding = {**msg.grounding, "edited_by_seller": True}
        msg.text = text.strip()[:4000]
    msg.status, msg.author_user_id = "queued", ctx.actor.id
    _queue_send(db, msg)
    log_action(
        db,
        msg.merchant_id,
        "customer_messaging",
        "send_message",
        "ai",
        key=f"msg:{msg.id}",
        resource_type="conversation",
        resource_id=msg.conversation_id,
        human_intervened=True,
    )
    conv = db.get(Conversation, msg.conversation_id)
    if conv is not None:
        conv.unread_count = 0
    return msg


def discard_suggestion(db: Session, ctx: TenantContext, message_id: uuid.UUID) -> None:
    msg = db.get(Message, message_id)
    if msg is None or msg.merchant_id != ctx.merchant_id or msg.status != "suggested":
        raise NotFound(code="suggestion_not_found")
    msg.status = "discarded"


def retry_failed(db: Session, ctx: TenantContext, message_id: uuid.UUID) -> Message:
    msg = db.get(Message, message_id)
    if msg is None or msg.merchant_id != ctx.merchant_id or msg.status != "failed":
        raise NotFound(code="message_not_found")
    msg.status, msg.error_code = "queued", None
    _queue_send(db, msg)
    return msg


# ----------------------------------------------------------------------------- triage
def assign(
    db: Session, ctx: TenantContext, conversation_id: uuid.UUID, user_id: uuid.UUID | None
) -> Conversation:
    conv = get_conversation(db, ctx, conversation_id, lock=True)
    if user_id is not None:
        member = db.scalar(
            select(Membership).where(Membership.user_id == user_id, Membership.status == "active")
        )
        if member is None:
            raise ValidationFailed("That person isn't on this team", code="assignee_not_member")
    conv.assigned_user_id = user_id
    audit.record(
        db,
        action="inbox.conversation_assigned",
        resource_type="conversation",
        resource_id=conv.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"user_id": str(user_id) if user_id else None},
    )
    return conv


def update_conversation(
    db: Session, ctx: TenantContext, conversation_id: uuid.UUID, fields: dict[str, Any]
) -> Conversation:
    conv = get_conversation(db, ctx, conversation_id, lock=True)
    if "status" in fields and fields["status"] not in ("open", "snoozed", "closed"):
        raise ValidationFailed(code="status_invalid")
    for k, v in fields.items():
        setattr(conv, k, v)
    if fields.get("human_handoff") is False:
        conv.escalated, conv.escalation_reason = False, None  # handed back to the AI
    if fields.get("status") == "closed":
        conv.unread_count = 0
        db.execute(
            update(OrderDraft)
            .where(
                OrderDraft.conversation_id == conv.id,
                OrderDraft.status.in_(("collecting", "awaiting_confirmation")),
            )
            .values(status="abandoned")
        )
    return conv


def mark_read(db: Session, ctx: TenantContext, conversation_id: uuid.UUID) -> Conversation:
    conv = get_conversation(db, ctx, conversation_id, lock=True)
    conv.unread_count = 0
    return conv


# ----------------------------------------------------------------------------- views
def message_view(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "direction": m.direction,
        "author_type": m.author_type,
        "author_user_id": m.author_user_id,
        "text": m.text,
        "status": m.status,
        "intent": m.intent,
        "confidence": m.confidence,
        "grounding": m.grounding,
        "error_code": m.error_code,
        "created_at": m.created_at,
        "sent_at": m.sent_at,
    }


def conversation_view(db: Session, c: Conversation, *, detail: bool = False) -> dict[str, Any]:
    cust = db.get(Customer, c.customer_id)
    last = db.scalar(
        select(Message)
        .where(Message.conversation_id == c.id, Message.status != "discarded")
        .order_by(Message.id.desc())
        .limit(1)
    )
    out: dict[str, Any] = {
        "id": c.id,
        "provider": c.provider,
        "connection_id": c.connection_id,
        "status": c.status,
        "customer": {"id": cust.id, "display_name": cust.display_name, "phone": cust.phone} if cust else None,
        "assigned_user_id": c.assigned_user_id,
        "labels": c.labels,
        "last_intent": c.last_intent,
        "human_handoff": c.human_handoff,
        "escalated": c.escalated,
        "escalation_reason": c.escalation_reason,
        "unread_count": c.unread_count,
        "locale": c.locale,
        "last_message_at": c.last_message_at,
        "first_response_due_at": c.first_response_due_at,
        "last_message": {"text": last.text[:200], "direction": last.direction, "status": last.status}
        if last
        else None,
    }
    if detail:
        draft = db.scalar(
            select(OrderDraft)
            .where(OrderDraft.conversation_id == c.id)
            .order_by(OrderDraft.created_at.desc())
            .limit(1)
        )
        out["ai_summary"] = c.ai_summary
        out["ai_summary_at"] = c.ai_summary_at
        out["order_draft"] = (
            {
                "id": draft.id,
                "status": draft.status,
                "fields": draft.fields,
                "awaiting_field": draft.awaiting_field,
                "order_id": draft.order_id,
            }
            if draft
            else None
        )
    return out


@customers.merge_hook
def _merge_conversations(db: Session, merchant_id: uuid.UUID, source: uuid.UUID, target: uuid.UUID) -> None:
    db.execute(
        update(Conversation)
        .where(Conversation.merchant_id == merchant_id, Conversation.customer_id == source)
        .values(customer_id=target)
    )


def conflict_if_closed(conv: Conversation) -> None:
    if conv.status == "closed":
        raise Conflict("This conversation is closed", code="conversation_closed")
