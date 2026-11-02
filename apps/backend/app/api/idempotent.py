"""Route helper wrapping a handler body in the idempotency protocol."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.domains.platform import idempotency


def run_idempotent(
    db: Session,
    *,
    key: str | None,
    owner: str,
    scope: str,
    body: Any,
    status_code: int,
    fn: Callable[[], Any],
) -> Any:
    """Execute ``fn`` honoring an optional Idempotency-Key. Returns a JSONResponse on replay."""
    if not key:
        return fn()
    outcome = idempotency.begin(owner, scope, key, idempotency.request_fingerprint(jsonable_encoder(body)))
    if isinstance(outcome, idempotency.Replay):
        return JSONResponse(outcome.body, status_code=outcome.status, headers={"Idempotent-Replayed": "true"})
    try:
        result = fn()
        idempotency.complete(db, outcome, status_code, jsonable_encoder(result))
        db.flush()
        return result
    except Exception:
        db.rollback()
        idempotency.abandon(outcome)
        raise
