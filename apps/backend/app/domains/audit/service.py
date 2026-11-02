"""Audit trail writer. Called inside the same transaction as the change it records, so an audit row
exists iff the change committed."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import Actor, RequestMeta
from app.core.logging import _redact
from app.core.tracing import current_trace_id
from app.domains.audit.models import AuditLog


def record(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None,
    actor: Actor,
    merchant_id: uuid.UUID | None,
    meta: RequestMeta | None = None,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    m = meta or RequestMeta()
    entry = AuditLog(
        merchant_id=merchant_id,
        actor_type=actor.type,
        actor_id=actor.id,
        actor_display=actor.display,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        source=m.source,
        request_id=m.request_id,
        trace_id=m.trace_id or current_trace_id(),
        ip=m.ip,
        user_agent=(m.user_agent or "")[:512] or None,
        changes=_redact(changes) if changes else None,
        meta=_redact(metadata) if metadata else None,
    )
    db.add(entry)
    return entry


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """{field: [old, new]} for changed fields only."""
    return {k: [before.get(k), v] for k, v in after.items() if before.get(k) != v}
