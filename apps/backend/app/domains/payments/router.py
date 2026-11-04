from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.errors import ValidationFailed
from app.domains.orders import service as orders
from app.domains.payments import service
from app.domains.payments.models import Payment

router = APIRouter(tags=["payments"])
webhooks_router = APIRouter(tags=["webhooks"])


class StartIn(BaseModel):
    return_url: str | None = Field(default=None, max_length=500)


class ManualIn(BaseModel):
    amount_minor: int = Field(gt=0, le=10_000_000_000, strict=True)
    method: str = Field(pattern=f"^({'|'.join(service.MANUAL_METHODS)})$")
    reference: str | None = Field(default=None, max_length=120)


@router.get("/orders/{order_id}/payments")
def list_payments(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    rows = db.scalars(select(Payment).where(Payment.order_id == o.id).order_by(Payment.id))
    return {"items": [service.payment_view(p) for p in rows]}


@router.post("/orders/{order_id}/payments/online", status_code=201)
def start_online(
    order_id: uuid.UUID,
    body: StartIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """A payment link for the customer (prepaid orders). Paid only after server-side verification."""
    return service.payment_view(service.start_online_payment(db, ctx, order_id, body.return_url))


@router.post("/payments/{payment_id}/verify")
def verify(
    payment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    p = db.get(Payment, payment_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        from app.core.errors import NotFound

        raise NotFound(code="payment_not_found")
    return service.payment_view(service.verify(db, p.id))


@router.post("/orders/{order_id}/payments/manual", status_code=201)
def record_manual(
    order_id: uuid.UUID,
    body: ManualIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    if not idem:
        raise ValidationFailed(
            "Idempotency-Key header is required for recording payments", code="idempotency_key_required"
        )
    return service.payment_view(
        service.record_manual(
            db,
            ctx,
            order_id,
            amount_minor=body.amount_minor,
            method=body.method,
            reference=body.reference,
            key=idem,
        )
    )


@router.post("/orders/{order_id}/switch-to-cod")
def switch_to_cod(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return orders.order_view(db, service.switch_to_cod(db, ctx, order_id), detail=True)


@router.get("/payments/cod/summary")
def cod_summary(
    ctx: TenantContext = Depends(require("payments.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return service.cod_summary(db, ctx)


@webhooks_router.post("/webhooks/payments/{provider}")
async def payment_webhook(provider: str, request: Request) -> JSONResponse:
    """Public, signature-verified. Records + dedupes, answers fast, verifies with the provider later."""
    from starlette.concurrency import run_in_threadpool

    body = await request.body()

    def _ingest() -> dict[str, int]:
        from app.core.db import session_scope

        with session_scope() as db:
            return service.ingest_payment_webhook(db, provider, dict(request.headers), body)

    try:
        stats = await run_in_threadpool(_ingest)
    except Exception as e:
        if getattr(e, "code", None) == "webhook_signature_invalid":
            return JSONResponse(
                {
                    "error": {
                        "code": "webhook_signature_invalid",
                        "message": "Invalid signature",
                        "details": {},
                        "request_id": request.state.request_id,
                    }
                },
                status_code=401,
            )
        raise
    return JSONResponse({"received": True, **stats})
