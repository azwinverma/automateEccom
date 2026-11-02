from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.pagination import build_page, paginate_desc
from app.domains.audit.models import AuditLog

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def list_audit_logs(
    action: str | None = Query(None, max_length=100),
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = Query(None, max_length=64),
    resource_id: str | None = Query(None, max_length=64),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("audit.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    # AuditLog is not TenantScoped (platform events have no tenant), so filter explicitly.
    stmt = select(AuditLog).where(AuditLog.merchant_id == ctx.merchant_id)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    rows = list(db.scalars(paginate_desc(stmt, AuditLog.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {
        "items": [
            {
                "id": a.id,
                "occurred_at": a.occurred_at,
                "actor": {"type": a.actor_type, "id": a.actor_id, "display": a.actor_display},
                "action": a.action,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "source": a.source,
                "request_id": a.request_id,
                "ip": a.ip,
                "changes": a.changes,
                "metadata": a.meta,
            }
            for a in items
        ],
        "next_cursor": nxt,
    }
