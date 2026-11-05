"""Typed workflow actions (AUT-004). Each declares its risk class, financial impact, the subjects it
works on and a capability check. Executors call the same Commerce Core services the seller uses, with
an idempotency key of workflow run + step, so a retried step can never act twice."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.errors import AppError, ValidationFailed

ORDERISH = ("order", "shipment", "return")
RETRYABLE_CODES = frozenset({"courier_unavailable", "provider_unavailable", "dependency_unavailable"})
PLACEHOLDERS = ("number", "name", "shop", "tracking")


@dataclass(frozen=True)
class ActionDef:
    code: str
    risk: str
    subjects: tuple[str, ...]
    run: Callable[[Session, TenantContext, dict[str, Any], dict[str, Any], str], dict[str, Any]]
    capable: Callable[[Session, dict[str, Any]], bool] = lambda db, f: True
    impact: Callable[[Session, dict[str, Any]], int | None] = lambda db, f: None
    confidence: Callable[[dict[str, Any]], float] = lambda f: 1.0
    threshold_key: str | None = None
    params: tuple[str, ...] = ()
    required_params: tuple[str, ...] = field(default=())


def _fill(text: str, facts: dict[str, Any], db: Session) -> str:
    from app.domains.merchants.models import Merchant

    o = facts.get("_order")
    m = db.get(Merchant, o.merchant_id) if o is not None else None
    values = {
        "number": f"#{facts.get('order.number', '')}",
        "name": facts.get("order.customer_name") or "",
        "shop": m.name if m else "",
        "tracking": facts.get("shipment.tracking_number") or "",
    }
    out = text
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    return out.strip()


# ----------------------------------------------------------------------------- executors
def _notify_seller(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.accounts.models import User
    from app.domains.integrations import registry
    from app.domains.merchants.models import Membership

    text = _fill(p.get("message") or "", f, db) or "A workflow needs your attention."
    rows = db.execute(
        select(User.email)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.merchant_id == ctx.merchant_id,
            Membership.role.in_(("owner", "admin")),
            Membership.status == "active",
        )
    ).all()
    sent = 0
    try:
        mailer = registry.mailer()
        for (email,) in rows:
            mailer.send_email(email, f"Nivaro: {text[:60]}", text, idempotency_key=f"{key}:{email}")
            sent += 1
    except registry.AdapterNotAvailable:
        pass  # production email isn't configured yet (GAP-EMAIL); the run log still shows the notice
    return {"recipients": sent, "message": text}


def _add_note(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.orders import service as orders

    o = f["_order"]
    note = _fill(p.get("note") or "", f, db)[:2000]
    orders.add_note(db, ctx, o.id, note)
    return {"note": note}


def _has_chat(db: Session, f: dict[str, Any]) -> bool:
    return bool(f.get("order.has_chat"))


def _send_message(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.fulfillment.service import _conversation_for
    from app.domains.inbox import service as inbox
    from app.domains.inbox.models import Message

    o = f["_order"]
    conv = _conversation_for(db, o)
    if conv is None:
        raise AppError("No chat with this customer", code="automation_no_chat")
    existing = db.scalar(
        select(Message.id).where(
            Message.conversation_id == conv.id, Message.grounding["workflow_key"].astext == key
        )
    )
    if existing is not None:
        return {"message_id": str(existing), "duplicate": True}
    chosen = p.get("text_ne") if conv.locale == "ne" and p.get("text_ne") else p.get("text_en")
    text = _fill(str(chosen or ""), f, db)
    if not text:
        raise ValidationFailed(code="automation_message_empty")
    msg = inbox.queue_reply(
        db, conv, text, author="system", intent="workflow", grounding={"workflow_key": key}
    )
    return {"message_id": str(msg.id), "locale": conv.locale}


REVIEW_TEXT = {
    "en": "Hi {name}! We hope you love your order {number}. Could you tell us how it went? Your review helps {shop} a lot.",
    "ne": "नमस्ते {name}! तपाईंलाई अर्डर {number} मन पर्‍यो होला। कस्तो लाग्यो भनिदिनुहुन्छ? तपाईंको प्रतिक्रियाले {shop} लाई धेरै सहयोग गर्छ।",
}


def _review_request(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    return _send_message(
        db,
        ctx,
        f,
        {"text_en": p.get("text_en") or REVIEW_TEXT["en"], "text_ne": p.get("text_ne") or REVIEW_TEXT["ne"]},
        key,
    )


def _courier_quote(db: Session, f: dict[str, Any]) -> dict[str, Any] | None:
    from app.domains.fulfillment import couriers

    o = f.get("_order")
    if o is None:
        return None
    ctx = TenantContext(merchant_id=o.merchant_id, actor=Actor.system("automation"))
    opts = couriers.courier_options(
        db, ctx, o, couriers.get_settings_row(db, o.merchant_id).default_weight_grams
    )
    rec = opts["recommendation"]
    if rec is None:
        return None
    pick = next(x for x in opts["options"] if x["recommended"])
    return {"rec": rec, "pick": pick}


def _can_book(db: Session, f: dict[str, Any]) -> bool:
    from app.domains.fulfillment.models import Shipment

    o = f.get("_order")
    if o is None or o.status not in ("cod_pending", "ready_to_ship"):
        return False
    live = db.scalar(
        select(Shipment.id).where(
            Shipment.order_id == o.id, Shipment.status != "cancelled", Shipment.direction == "outbound"
        )
    )
    return live is None and _courier_quote(db, f) is not None


def _book_impact(db: Session, f: dict[str, Any]) -> int | None:
    q = _courier_quote(db, f)
    return q["pick"]["price"]["amount_minor"] if q and q["pick"]["price"] else None


def _book(db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str) -> dict[str, Any]:
    from app.domains.fulfillment import service as fulfillment

    q = _courier_quote(db, f)
    if q is None:
        raise AppError("No courier can take this parcel", code="automation_no_courier")
    s = fulfillment.book(
        db,
        ctx,
        f["_order"].id,
        fulfillment.BookInput(
            courier_account_id=q["rec"]["courier_account_id"], service_code=q["rec"]["service_code"]
        ),
        f"wf:{key}",
    )
    return {
        "shipment_id": str(s.id),
        "tracking_number": s.tracking_number,
        "courier": s.courier_name,
        "reason": q["rec"]["reason"],
    }


def _booked_shipment(db: Session, f: dict[str, Any]) -> Any:
    from app.domains.fulfillment.models import Shipment

    s = f.get("_shipment")
    if s is not None:
        return s if s.status == "booked" else None
    o = f.get("_order")
    if o is None:
        return None
    return db.scalar(
        select(Shipment).where(
            Shipment.order_id == o.id, Shipment.status == "booked", Shipment.direction == "outbound"
        )
    )


def _pickup(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.fulfillment import service as fulfillment

    s = _booked_shipment(db, f)
    if s is None:
        return {"skipped": "nothing_booked"}
    fulfillment.request_pickup(db, ctx, [s.id])
    return {"shipment_id": str(s.id)}


def _reattempt(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.fulfillment import service as fulfillment

    s = f["_shipment"]
    if s.status != "delivery_failed":
        return {"skipped": f"status_{s.status}"}
    fulfillment.request_reattempt(
        db, ctx, s.id, note=(p.get("note") or "Automatic reattempt")[:500], by="automation"
    )
    return {"shipment_id": str(s.id)}


def _approve_return(
    db: Session, ctx: TenantContext, f: dict[str, Any], p: dict[str, Any], key: str
) -> dict[str, Any]:
    from app.domains.returns import service as returns

    r = f["_return"]
    if r.status != "requested":
        return {"skipped": f"status_{r.status}"}
    returns._approve(db, ctx, r, None, by="automation")
    return {"return_id": str(r.id)}


def _return_confidence(f: dict[str, Any]) -> float:
    # Outside policy or with warning signs: a person decides (never auto).
    return 0.4 if not f.get("return.eligible") or f.get("return.has_signals") else 1.0


ACTIONS: dict[str, ActionDef] = {
    a.code: a
    for a in (
        ActionDef(
            "notify_seller", "R0", (*ORDERISH, "variant", "channel"), _notify_seller, params=("message",)
        ),
        ActionDef("add_order_note", "R0", ORDERISH, _add_note, params=("note",), required_params=("note",)),
        ActionDef(
            "send_customer_message",
            "R1",
            ORDERISH,
            _send_message,
            capable=_has_chat,
            params=("text_en", "text_ne"),
            required_params=("text_en",),
        ),
        ActionDef(
            "send_review_request",
            "R2",
            ORDERISH,
            _review_request,
            capable=_has_chat,
            params=("text_en", "text_ne"),
        ),
        ActionDef("book_courier", "R1", ("order",), _book, capable=_can_book, impact=_book_impact),
        ActionDef(
            "request_pickup",
            "R1",
            ("order", "shipment"),
            _pickup,
            capable=lambda db, f: _booked_shipment(db, f) is not None,
        ),
        ActionDef(
            "request_reattempt",
            "R2",
            ("shipment",),
            _reattempt,
            capable=lambda db, f: (
                f.get("shipment.status") == "delivery_failed" and not f.get("shipment.manual")
            ),
            params=("note",),
        ),
        ActionDef(
            "approve_return",
            "R2",
            ("return",),
            _approve_return,
            capable=lambda db, f: f.get("return.status") == "requested",
            impact=lambda db, f: f.get("return.refund_due_minor"),
            confidence=_return_confidence,
            threshold_key="return_approve_minor",
        ),
    )
}


def validate_params(code: str, params: dict[str, Any], path: str) -> None:
    a = ACTIONS[code]
    unknown = [k for k in params if k not in a.params]
    missing = [k for k in a.required_params if not str(params.get(k) or "").strip()]
    if unknown or missing:
        raise ValidationFailed(
            code="workflow_invalid",
            details={"path": path, "reason": "params", "unknown": unknown, "missing": missing},
        )
    for k, v in params.items():
        if not isinstance(v, str) or len(v) > 1000:
            raise ValidationFailed(
                code="workflow_invalid", details={"path": path, "reason": "param_value", "param": k}
            )
