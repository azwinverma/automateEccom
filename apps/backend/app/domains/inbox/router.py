from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.pagination import build_page, paginate_desc
from app.domains.inbox import service
from app.domains.inbox.models import Conversation, Message

router = APIRouter(tags=["inbox"])


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ApproveIn(BaseModel):
    text: str | None = Field(default=None, max_length=4000)


class AssignIn(BaseModel):
    user_id: uuid.UUID | None = None


class ConversationPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|snoozed|closed)$")
    labels: list[str] | None = Field(default=None, max_length=10)
    human_handoff: bool | None = None


@router.get("/conversations")
def list_conversations(
    status: str | None = Query("open", pattern="^(open|snoozed|closed|all)$"),
    assigned: str | None = Query(None, pattern="^(me|unassigned)$"),
    escalated: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("inbox.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(Conversation)
    if status and status != "all":
        stmt = stmt.where(Conversation.status == status)
    if assigned == "me":
        stmt = stmt.where(Conversation.assigned_user_id == ctx.actor.id)
    elif assigned == "unassigned":
        stmt = stmt.where(Conversation.assigned_user_id.is_(None))
    if escalated is not None:
        stmt = stmt.where(Conversation.escalated.is_(escalated))
    rows = list(db.scalars(paginate_desc(stmt, Conversation.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    items.sort(key=lambda c: c.last_message_at or c.created_at, reverse=True)
    return {"items": [service.conversation_view(db, c) for c in items], "next_cursor": nxt}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inbox.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.conversation_view(db, service.get_conversation(db, ctx, conversation_id), detail=True)


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("inbox.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    conv = service.get_conversation(db, ctx, conversation_id)
    stmt = select(Message).where(Message.conversation_id == conv.id, Message.status != "discarded")
    rows = list(db.scalars(paginate_desc(stmt, Message.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {"items": [service.message_view(m) for m in reversed(items)], "next_cursor": nxt}


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def reply(
    conversation_id: uuid.UUID,
    body: ReplyIn,
    ctx: TenantContext = Depends(require("inbox.reply")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Seller reply. The AI steps back (human handoff) until handed back."""
    return service.message_view(service.send_seller_reply(db, ctx, conversation_id, body.text))


@router.post("/messages/{message_id}/approve")
def approve(
    message_id: uuid.UUID,
    body: ApproveIn,
    ctx: TenantContext = Depends(require("inbox.reply")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Send an AI suggestion, optionally edited."""
    return service.message_view(service.approve_suggestion(db, ctx, message_id, body.text))


@router.post("/messages/{message_id}/discard", status_code=204)
def discard(
    message_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inbox.reply")),
    db: Session = Depends(get_db, scope="function"),
) -> None:
    service.discard_suggestion(db, ctx, message_id)


@router.post("/messages/{message_id}/retry")
def retry(
    message_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inbox.reply")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.message_view(service.retry_failed(db, ctx, message_id))


@router.post("/conversations/{conversation_id}/assign")
def assign(
    conversation_id: uuid.UUID,
    body: AssignIn,
    ctx: TenantContext = Depends(require("inbox.assign")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.conversation_view(db, service.assign(db, ctx, conversation_id, body.user_id), detail=True)


@router.patch("/conversations/{conversation_id}")
def patch(
    conversation_id: uuid.UUID,
    body: ConversationPatch,
    ctx: TenantContext = Depends(require("inbox.reply")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    c = service.update_conversation(db, ctx, conversation_id, body.model_dump(exclude_unset=True))
    return service.conversation_view(db, c, detail=True)


@router.post("/conversations/{conversation_id}/read")
def read(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inbox.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.conversation_view(db, service.mark_read(db, ctx, conversation_id))


@router.post("/conversations/{conversation_id}/summary")
def summary(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inbox.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.domains.inbox.agent import summarize

    conv = service.get_conversation(db, ctx, conversation_id, lock=True)
    return {"summary": summarize(db, conv), "at": conv.ai_summary_at}
