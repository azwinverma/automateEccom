from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.api.idempotent import run_idempotent
from app.core.config import Environment, get_settings
from app.core.context import TenantContext
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import decode_cursor, encode_cursor
from app.domains.customers import service as customers
from app.domains.fulfillment import couriers, service, settlement
from app.domains.fulfillment.models import CODSettlement, Shipment
from app.domains.integrations import registry
from app.domains.integrations.base import FAILURE_REASONS
from app.domains.orders import service as orders

router = APIRouter(tags=["fulfillment"])
webhooks_router = APIRouter(tags=["webhooks"])
dev_router = APIRouter(include_in_schema=False)

MAX_FILE = 2 * 1024 * 1024


# ----------------------------------------------------------------------------- couriers
class PickupIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=20)
    district: str | None = Field(default=None, max_length=40)
    municipality: str | None = Field(default=None, max_length=120)
    area: str | None = Field(default=None, max_length=160)

    def to(self) -> couriers.PickupInput:
        return couriers.PickupInput(**self.model_dump())


class ConnectCourierIn(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    display_name: str | None = Field(default=None, max_length=120)
    credentials: dict[str, str] = Field(default_factory=dict, max_length=10)
    pickup: PickupIn = Field(default_factory=PickupIn)
    is_default: bool = False


class UpdateCourierIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    pickup: PickupIn | None = None
    is_default: bool | None = None


@router.get("/couriers/providers")
def courier_providers(ctx: TenantContext = Depends(require("fulfillment.read"))) -> dict[str, Any]:
    return {"items": registry.available("courier")}


@router.get("/couriers")
def list_couriers(
    ctx: TenantContext = Depends(require("fulfillment.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {"items": [couriers.account_view(a) for a in couriers.live_accounts(db)]}


@router.post("/couriers", status_code=201)
def connect_courier(
    body: ConnectCourierIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    a = couriers.connect(
        db, ctx, body.provider, body.display_name, body.credentials, body.pickup.to(), body.is_default
    )
    return couriers.account_view(a)


@router.patch("/couriers/{account_id}")
def update_courier(
    account_id: uuid.UUID,
    body: UpdateCourierIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    a = couriers.update_account(
        db,
        ctx,
        account_id,
        display_name=body.display_name,
        pickup=body.pickup.to() if body.pickup else None,
        make_default=body.is_default,
    )
    return couriers.account_view(a)


@router.delete("/couriers/{account_id}", status_code=204)
def disconnect_courier(
    account_id: uuid.UUID,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> None:
    couriers.disconnect(db, ctx, account_id)


# ----------------------------------------------------------------------------- settings + delivery fees
class SettingsIn(BaseModel):
    notify_customers: bool | None = None
    default_weight_grams: int | None = Field(default=None, ge=1, le=100000)
    recovery_wait_hours: int | None = Field(default=None, ge=1, le=168)


class FeeRuleIn(BaseModel):
    scope: Literal["default", "inside_valley", "district"]
    district: str | None = Field(default=None, max_length=40)
    fee_minor: int = Field(ge=0, le=100_000_000, strict=True)
    free_over_minor: int | None = Field(default=None, gt=0, le=10_000_000_000, strict=True)


class FeeRulesIn(BaseModel):
    rules: list[FeeRuleIn] = Field(max_length=100)


@router.get("/fulfillment/settings")
def get_fulfillment_settings(
    ctx: TenantContext = Depends(require("fulfillment.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return couriers.settings_view(couriers.get_settings_row(db, ctx.merchant_id))


@router.patch("/fulfillment/settings")
def update_fulfillment_settings(
    body: SettingsIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    row = couriers.get_settings_row(db, ctx.merchant_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(row, k, v)
    return couriers.settings_view(row)


@router.get("/fulfillment/delivery-fees")
def get_fee_rules(
    ctx: TenantContext = Depends(require("fulfillment.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return {"items": [couriers.fee_rule_view(r) for r in couriers.fee_rules(db)]}


@router.put("/fulfillment/delivery-fees")
def put_fee_rules(
    body: FeeRulesIn,
    ctx: TenantContext = Depends(require("settings.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    rows = couriers.replace_fee_rules(
        db,
        ctx,
        [couriers.FeeRuleInput(r.scope, r.fee_minor, r.district, r.free_over_minor) for r in body.rules],
    )
    db.flush()
    return {"items": [couriers.fee_rule_view(r) for r in rows]}


@router.get("/fulfillment/delivery-fee")
def quote_delivery_fee(
    district: str = Query(max_length=40),
    subtotal_minor: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return {"quote": couriers.quote_fee(db, district, subtotal_minor)}


# ----------------------------------------------------------------------------- rates + booking
@router.get("/couriers/rates")
def courier_rates(
    order_id: uuid.UUID,
    weight_grams: int | None = Query(default=None, ge=1, le=100000),
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Courier options for an order with a rule-based recommendation (Courier Brain arrives in Phase 6)."""
    o = orders.get_order(db, ctx, order_id)
    weight = weight_grams or couriers.get_settings_row(db, ctx.merchant_id).default_weight_grams
    return couriers.courier_options(db, ctx, o, weight)


class BookIn(BaseModel):
    courier_account_id: uuid.UUID
    weight_grams: int | None = Field(default=None, ge=1, le=100000)
    service_code: str | None = Field(default=None, max_length=40)
    tracking_number: str | None = Field(default=None, max_length=80)
    courier_name: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)


@router.post("/orders/{order_id}/shipments", status_code=201)
def book_shipment(
    order_id: uuid.UUID,
    body: BookIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key", max_length=160),
) -> Any:
    if not idem:
        raise ValidationFailed(
            "Idempotency-Key header is required for booking a courier", code="idempotency_key_required"
        )

    def _run() -> dict[str, Any]:
        s = service.book(db, ctx, order_id, service.BookInput(**body.model_dump()), idem)
        return service.shipment_view(db, s, detail=True)

    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope=f"POST /orders/{order_id}/shipments",
        body=body,
        status_code=201,
        fn=_run,
    )


@router.get("/orders/{order_id}/shipments")
def order_shipments(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    rows = db.scalars(select(Shipment).where(Shipment.order_id == o.id).order_by(Shipment.id.desc()))
    return {"items": [service.shipment_view(db, s, detail=True, order=o) for s in rows]}


# ----------------------------------------------------------------------------- shipments
@router.get("/shipments")
def list_shipments(
    bucket: str | None = Query(
        default=None, pattern="^(to_pickup|in_transit|attention|delivered|returned|cancelled)$"
    ),
    courier_account_id: uuid.UUID | None = None,
    q: str | None = Query(default=None, max_length=80),
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    from app.domains.orders.models import Order

    stmt = select(Shipment, Order).join(Order, Order.id == Shipment.order_id)
    if bucket:
        stmt = stmt.where(Shipment.status.in_(service.BUCKETS[bucket]))
    if courier_account_id:
        stmt = stmt.where(Shipment.courier_account_id == courier_account_id)
    if q:
        term = q.strip().lstrip("#")
        conds: list[Any] = [Shipment.tracking_number.ilike(f"%{term}%"), Order.ship_name.ilike(f"%{term}%")]
        if term.isdigit():
            conds.append(Order.number == int(term))
        from sqlalchemy import or_

        stmt = stmt.where(or_(*conds))
    if cursor:
        stmt = stmt.where(Shipment.id < decode_cursor(cursor))
    rows = db.execute(stmt.order_by(Shipment.id.desc()).limit(limit + 1)).all()
    items = [service.shipment_view(db, s, order=o) for s, o in rows[:limit]]
    return {
        "items": items,
        "next_cursor": encode_cursor(rows[limit - 1][0].id) if len(rows) > limit else None,
        "counts": service.counts(db),
    }


@router.get("/shipments/{shipment_id}")
def get_shipment(
    shipment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.shipment_view(db, service.get_shipment(db, ctx, shipment_id), detail=True)


@router.get("/shipments/{shipment_id}/label")
def shipment_label(
    shipment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.label(db, ctx, shipment_id)


class PickupRequestIn(BaseModel):
    shipment_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


@router.post("/shipments/pickup")
def request_pickup(
    body: PickupRequestIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    rows = service.request_pickup(db, ctx, body.shipment_ids)
    return {"items": [service.shipment_view(db, s) for s in rows]}


class ReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


@router.post("/shipments/{shipment_id}/cancel")
def cancel_shipment(
    shipment_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.shipment_view(db, service.cancel(db, ctx, shipment_id, reason=body.reason), detail=True)


@router.post("/shipments/{shipment_id}/refresh")
def refresh_tracking(
    shipment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("fulfillment.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.shipment_view(db, service.refresh(db, ctx, shipment_id), detail=True)


class ManualStatusIn(BaseModel):
    status: str = Field(max_length=24)
    failure_reason: str | None = Field(default=None, pattern=f"^({'|'.join(FAILURE_REASONS)})$")
    note: str | None = Field(default=None, max_length=500)


@router.post("/shipments/{shipment_id}/status")
def manual_status(
    shipment_id: uuid.UUID,
    body: ManualStatusIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    s = service.manual_update(
        db, ctx, shipment_id, body.status, failure_reason=body.failure_reason, note=body.note
    )
    return service.shipment_view(db, s, detail=True)


class TrackingIn(BaseModel):
    tracking_number: str = Field(min_length=1, max_length=80)
    courier_name: str | None = Field(default=None, max_length=80)


@router.post("/shipments/{shipment_id}/tracking")
def set_tracking(
    shipment_id: uuid.UUID,
    body: TrackingIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    s = service.set_tracking(db, ctx, shipment_id, body.tracking_number, body.courier_name)
    return service.shipment_view(db, s, detail=True)


class AddressIn(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=7, max_length=20)
    province: str = Field(default="", max_length=20)
    district: str = Field(min_length=2, max_length=40)
    municipality: str = Field(min_length=2, max_length=120)
    ward: int = Field(ge=1, le=35)
    area: str | None = Field(default=None, max_length=160)
    landmark: str | None = Field(default=None, max_length=200)


class ReattemptIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    address: AddressIn | None = None


@router.post("/shipments/{shipment_id}/reattempt")
def reattempt(
    shipment_id: uuid.UUID,
    body: ReattemptIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    addr = customers.AddressInput(**body.address.model_dump()) if body.address else None
    s = service.request_reattempt(db, ctx, shipment_id, note=body.note, address=addr)
    return service.shipment_view(db, s, detail=True)


@router.post("/shipments/{shipment_id}/return")
def return_to_sender(
    shipment_id: uuid.UUID,
    body: ReasonIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    s = service.return_to_sender(db, ctx, shipment_id, reason=body.reason)
    return service.shipment_view(db, s, detail=True)


@router.post("/shipments/{shipment_id}/received-back")
def received_back(
    shipment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("inventory.adjust")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    s = service.confirm_received_back(db, ctx, shipment_id)
    return service.shipment_view(db, s, detail=True)


# ----------------------------------------------------------------------------- COD settlements
@router.get("/cod/overview")
def cod_overview(
    ctx: TenantContext = Depends(require("payments.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return settlement.overview(db, ctx)


@router.get("/cod/awaiting")
def cod_awaiting(
    courier_account_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(require("payments.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return {"items": settlement.awaiting(db, courier_account_id=courier_account_id)}


@router.get("/cod/settlements")
def list_settlements(
    status: str | None = Query(default=None, pattern="^(needs_review|reconciled|confirmed)$"),
    ctx: TenantContext = Depends(require("payments.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(CODSettlement).order_by(CODSettlement.id.desc()).limit(200)
    if status:
        stmt = stmt.where(CODSettlement.status == status)
    return {"items": [settlement.settlement_view(db, st) for st in db.scalars(stmt)]}


@router.get("/cod/settlements/{settlement_id}")
def get_settlement(
    settlement_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return settlement.settlement_view(db, settlement.get_settlement(db, ctx, settlement_id), detail=True)


@router.post("/cod/settlements/import", status_code=201)
async def import_settlement(
    request: Request,
    courier_account_id: uuid.UUID = Form(...),
    reference: str = Form(min_length=1, max_length=120),
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Any:
    from starlette.concurrency import run_in_threadpool

    content = await file.read(MAX_FILE + 1)
    if len(content) > MAX_FILE:
        raise ValidationFailed("The file is larger than 2 MB", code="settlement_file_too_large")

    def _run() -> tuple[dict[str, Any], bool]:
        st, created = settlement.import_file(db, ctx, courier_account_id, reference, content)
        return settlement.settlement_view(db, st, detail=True), created

    view, created = await run_in_threadpool(_run)
    return view if created else JSONResponse(_jsonable(view), status_code=200)


def _jsonable(v: Any) -> Any:
    from fastapi.encoders import jsonable_encoder

    return jsonable_encoder(v)


class CashIn(BaseModel):
    courier_account_id: uuid.UUID
    shipment_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    reference: str | None = Field(default=None, max_length=120)


@router.post("/cod/settlements/cash", status_code=201)
def record_cash(
    body: CashIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    st = settlement.record_cash(db, ctx, body.courier_account_id, body.shipment_ids, body.reference)
    return settlement.settlement_view(db, st, detail=True)


@router.post("/cod/settlements/{settlement_id}/recheck")
def recheck_settlement(
    settlement_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return settlement.settlement_view(db, settlement.recheck(db, ctx, settlement_id), detail=True)


class AcceptIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/cod/settlement-lines/{line_id}/accept")
def accept_line(
    line_id: uuid.UUID,
    body: AcceptIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return settlement.settlement_view(db, settlement.accept_line(db, ctx, line_id, body.reason), detail=True)


class ConfirmIn(BaseModel):
    bank_reference: str | None = Field(default=None, max_length=120)


@router.post("/cod/settlements/{settlement_id}/confirm")
def confirm_settlement(
    settlement_id: uuid.UUID,
    body: ConfirmIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    st = settlement.confirm(db, ctx, settlement_id, body.bank_reference)
    return settlement.settlement_view(db, st, detail=True)


# ----------------------------------------------------------------------------- courier webhooks
@webhooks_router.post("/webhooks/couriers/{provider}/{account_id}")
async def courier_webhook(provider: str, account_id: uuid.UUID, request: Request) -> JSONResponse:
    """Public, signature-verified with the account's own secret. Records + dedupes, answers fast."""
    from starlette.concurrency import run_in_threadpool

    from app.core.db import session_scope

    body = await request.body()

    def _ingest() -> dict[str, int]:
        with session_scope() as db:
            return service.ingest_courier_webhook(db, provider, account_id, dict(request.headers), body)

    try:
        stats = await run_in_threadpool(_ingest)
    except Exception as e:
        code = getattr(e, "code", None)
        if code in ("webhook_signature_invalid", "provider_not_available", "webhook_malformed"):
            status = {"webhook_signature_invalid": 401, "provider_not_available": 404}.get(code, 400)
            return JSONResponse(
                {
                    "error": {
                        "code": code,
                        "message": str(getattr(e, "message", code)),
                        "details": {},
                        "request_id": request.state.request_id,
                    }
                },
                status_code=status,
            )
        raise
    return JSONResponse(stats)


# ----------------------------------------------------------------------------- dev simulator
def _dev_only() -> None:
    if get_settings().environment in (Environment.PRODUCTION, Environment.STAGING):
        raise NotFound()


class SimulateIn(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=80)
    status: str = Field(max_length=24)
    failure_reason: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=160)


@dev_router.post("/_dev/couriers/sandbox/{account_id}/simulate")
def simulate_courier_event(
    account_id: uuid.UUID,
    body: SimulateIn,
    ctx: TenantContext = Depends(require("fulfillment.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Dev only: the sandbox courier records a status and pushes a signed webhook through the real
    public endpoint path (signature check, dedupe, outbox, worker)."""
    _dev_only()
    from app.domains.integrations.sandbox import SandboxCourierAdapter

    a = couriers.get_account(db, ctx, account_id)
    if a.provider != SandboxCourierAdapter.code:
        raise NotFound(code="courier_not_found")
    s = db.scalar(
        select(Shipment).where(
            Shipment.courier_account_id == a.id, Shipment.tracking_number == body.tracking_number
        )
    )
    if s is None:
        raise NotFound(code="shipment_not_found")
    payload = SandboxCourierAdapter.simulate(
        body.tracking_number,
        body.status,
        failure_reason=body.failure_reason,
        cod_collected_minor=s.cod_amount_minor if body.status == "delivered" else None,
        location=body.location,
    )
    raw = json.dumps(payload).encode()
    secret = couriers.webhook_secret(a) or ""
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    stats = service.ingest_courier_webhook(db, a.provider, a.id, {"x-sandbox-signature": sig}, raw)
    return {"event": payload, **stats}


class DevSettlementIn(BaseModel):
    fee_minor: int = Field(default=10000, ge=0, le=1_000_000)
    short_minor: int = Field(default=0, ge=0, le=1_000_000)  # make the first line short (mismatch)
    extra_unknown: bool = False


@dev_router.post("/_dev/couriers/sandbox/{account_id}/settlement", status_code=201)
def simulate_settlement(
    account_id: uuid.UUID,
    body: DevSettlementIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Dev only: the sandbox courier issues a statement for its delivered, unsettled COD parcels,
    then Nivaro fetches it through the adapter like the daily sync does."""
    _dev_only()
    from datetime import UTC, datetime

    from app.domains.integrations.base import SettlementLineData, SettlementReport
    from app.domains.integrations.sandbox import SandboxCourierAdapter

    a = couriers.get_account(db, ctx, account_id)
    if a.provider != SandboxCourierAdapter.code:
        raise NotFound(code="courier_not_found")
    rows = settlement.awaiting(db, courier_account_id=a.id)
    lines = [
        SettlementLineData(
            r["tracking_number"],
            r["cod_amount"]["amount_minor"] - (body.short_minor if i == 0 else 0),
            body.fee_minor,
        )
        for i, r in enumerate(rows)
    ]
    if body.extra_unknown:
        lines.append(SettlementLineData("SBXUNKNOWN01", 50000, body.fee_minor))
    if not lines:
        raise ValidationFailed(
            "No delivered COD parcels are waiting for settlement", code="nothing_to_settle"
        )
    ref = f"SBX-STMT-{datetime.now(UTC):%Y%m%d%H%M%S%f}"
    SandboxCourierAdapter.settlement_reports.setdefault(str(a.id), []).append(
        SettlementReport(reference=ref, currency="NPR", lines=lines)
    )
    imported = settlement.sync_account(db, a)
    st = db.scalar(
        select(CODSettlement).where(CODSettlement.courier_account_id == a.id, CODSettlement.reference == ref)
    )
    return {
        "imported": imported,
        "settlement": settlement.settlement_view(db, st, detail=True) if st else None,
    }
