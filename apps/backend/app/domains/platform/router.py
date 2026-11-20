from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant
from app.core.context import TenantContext
from app.core.db import get_engine
from app.core.redis import get_redis
from app.domains.platform import flags

health_router = APIRouter(tags=["ops"])
router = APIRouter(tags=["platform"])


@health_router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get("/readyz")
def readyz() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
    try:
        get_redis().ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {type(e).__name__}"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503
    )


@health_router.get("/metrics")
def metrics() -> PlainTextResponse:
    from app.domains.platform import ops

    ops.collect()  # database/Redis-backed operational gauges (cached for 15 s)
    return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)


@router.get("/feature-flags")
def feature_flags(
    ctx: TenantContext = Depends(get_tenant), db: Session = Depends(get_db, scope="function")
) -> dict:
    return {"flags": flags.evaluate_all(db, ctx.merchant_id)}
