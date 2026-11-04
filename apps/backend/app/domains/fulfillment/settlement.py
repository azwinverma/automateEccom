"""COD settlement reconciliation (FUL-010, PAY-002, PAY-010).

Couriers collect cash at the door and pay it to the merchant later, minus their charges, with a
statement. Each statement line is matched to our shipment by tracking number:

* matched: delivered COD parcel, collected amount equals what we asked the courier to collect;
* amount_mismatch / not_delivered / unknown_shipment / already_settled / duplicate_in_report /
  not_cod: shown to the seller, who can recheck later or accept the line with a reason (audited).

Only when every line is matched or accepted can the seller confirm the money arrived; confirming
marks those COD records settled. Statements are idempotent per (courier account, reference).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.fulfillment import couriers
from app.domains.fulfillment.models import CODSettlement, CODSettlementLine, CourierAccount, Shipment
from app.domains.integrations.base import (
    CourierCapability,
    IntegrationError,
    SettlementLineData,
    SettlementReport,
)
from app.domains.orders.models import Order
from app.domains.payments.models import CODRecord

log = structlog.get_logger(__name__)

MAX_ROWS = 5000
TRACKING_COLS = (
    "tracking_number",
    "tracking",
    "tracking_no",
    "awb",
    "awb_no",
    "consignment",
    "consignment_no",
)
COLLECTED_COLS = ("cod_collected", "cod_amount", "collected", "collected_amount", "cod", "cash_collected")
FEE_COLS = (
    "delivery_charge",
    "delivery_fee",
    "shipping_charge",
    "charge",
    "fee",
    "service_charge",
    "cod_fee",
    "cod_charge",
)
RESOLVED = ("matched",)


def get_settlement(
    db: Session, ctx: TenantContext, settlement_id: uuid.UUID, *, lock: bool = False
) -> CODSettlement:
    stmt = select(CODSettlement).where(CODSettlement.id == settlement_id)
    if lock:
        stmt = stmt.with_for_update()
    st = db.scalar(stmt)
    if st is None or st.merchant_id != ctx.merchant_id:
        raise NotFound(code="settlement_not_found")
    return st


# ----------------------------------------------------------------------------- matching
def _settled_elsewhere(db: Session, shipment_id: uuid.UUID, settlement_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(CODSettlementLine.id)
            .join(CODSettlement, CODSettlement.id == CODSettlementLine.settlement_id)
            .where(
                CODSettlementLine.shipment_id == shipment_id,
                CODSettlementLine.settlement_id != settlement_id,
                CODSettlement.status == "confirmed",
            )
            .limit(1)
        )
        is not None
    )


def _match(db: Session, st: CODSettlement, line: CODSettlementLine, seen: set[str]) -> None:
    s = db.scalar(
        select(Shipment).where(
            Shipment.courier_account_id == st.courier_account_id,
            Shipment.tracking_number == line.tracking_number,
        )
    )
    line.shipment_id = s.id if s else None
    line.order_id = s.order_id if s else None
    line.expected_minor = s.cod_amount_minor if s else None
    if line.tracking_number in seen:
        line.match_status = "duplicate_in_report"
    elif s is None:
        line.match_status = "unknown_shipment"
    elif s.cod_amount_minor == 0:
        line.match_status = "matched" if line.collected_minor == 0 else "not_cod"
    elif _settled_elsewhere(db, s.id, st.id):
        line.match_status = "already_settled"
    elif s.status != "delivered":
        line.match_status = "not_delivered"
    elif line.collected_minor != s.cod_amount_minor:
        line.match_status = "amount_mismatch"
    else:
        line.match_status = "matched"
    seen.add(line.tracking_number)


def _totals(db: Session, st: CODSettlement) -> None:
    lines = list(db.scalars(select(CODSettlementLine).where(CODSettlementLine.settlement_id == st.id)))
    st.line_count = len(lines)
    st.collected_minor = sum(x.collected_minor for x in lines)
    st.fees_minor = sum(x.fee_minor for x in lines)
    st.net_minor = st.collected_minor - st.fees_minor
    st.expected_minor = sum(x.expected_minor or 0 for x in lines)
    st.issue_count = sum(1 for x in lines if x.match_status not in RESOLVED and x.accepted_at is None)
    if st.status != "confirmed":
        st.status = "reconciled" if st.issue_count == 0 else "needs_review"


def import_report(
    db: Session,
    account: CourierAccount,
    report: SettlementReport,
    source: str,
    user_id: uuid.UUID | None = None,
) -> tuple[CODSettlement, bool]:
    """Returns (settlement, created). Re-importing the same reference returns the existing one."""
    existing = db.scalar(
        select(CODSettlement).where(
            CODSettlement.courier_account_id == account.id, CODSettlement.reference == report.reference
        )
    )
    if existing is not None:
        return existing, False
    st = CODSettlement(
        merchant_id=account.merchant_id,
        courier_account_id=account.id,
        provider=account.provider,
        source=source,
        reference=report.reference[:120],
        currency=report.currency,
        period_start=report.period_start,
        period_end=report.period_end,
        imported_by_user_id=user_id,
    )
    db.add(st)
    db.flush()
    seen: set[str] = set()
    for ld in report.lines:
        line = CODSettlementLine(
            merchant_id=account.merchant_id,
            settlement_id=st.id,
            tracking_number=ld.tracking_number.strip()[:80],
            collected_minor=ld.collected_minor,
            fee_minor=ld.fee_minor,
            match_status="unknown_shipment",
            note=(ld.note or "")[:300] or None,
        )
        _match(db, st, line, seen)
        db.add(line)
    db.flush()
    _totals(db, st)
    return st, True


def recheck(db: Session, ctx: TenantContext, settlement_id: uuid.UUID) -> CODSettlement:
    """Re-match open lines (e.g. a parcel was marked delivered after the statement arrived)."""
    st = get_settlement(db, ctx, settlement_id, lock=True)
    if st.status == "confirmed":
        return st
    seen: set[str] = set()
    for line in db.scalars(
        select(CODSettlementLine)
        .where(CODSettlementLine.settlement_id == st.id)
        .order_by(CODSettlementLine.id)
    ):
        if line.accepted_at is None:
            _match(db, st, line, seen)
        else:
            seen.add(line.tracking_number)
    db.flush()
    _totals(db, st)
    return st


def accept_line(db: Session, ctx: TenantContext, line_id: uuid.UUID, reason: str) -> CODSettlement:
    line = db.get(CODSettlementLine, line_id)
    if line is None or line.merchant_id != ctx.merchant_id:
        raise NotFound(code="settlement_line_not_found")
    st = get_settlement(db, ctx, line.settlement_id, lock=True)
    if st.status == "confirmed":
        raise Conflict("This settlement is already confirmed", code="settlement_confirmed")
    if line.match_status in RESOLVED or line.accepted_at is not None:
        return st
    line.accepted_at, line.accepted_by_user_id, line.accept_reason = utcnow(), ctx.actor.id, reason[:300]
    audit.record(
        db,
        action="fulfillment.settlement_line_accepted",
        resource_type="cod_settlement",
        resource_id=st.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={
            "tracking_number": line.tracking_number,
            "match_status": line.match_status,
            "collected_minor": line.collected_minor,
            "expected_minor": line.expected_minor,
            "reason": reason[:300],
        },
    )
    db.flush()
    _totals(db, st)
    return st


def confirm(
    db: Session, ctx: TenantContext, settlement_id: uuid.UUID, bank_reference: str | None
) -> CODSettlement:
    st = get_settlement(db, ctx, settlement_id, lock=True)
    if st.status == "confirmed":
        return st
    _totals(db, st)
    if st.issue_count:
        raise Conflict(
            "Some lines don't match yet. Recheck them or accept each with a reason.",
            code="settlement_has_issues",
            details={"issues": st.issue_count},
        )
    now = utcnow()
    settled = 0
    for line in db.scalars(select(CODSettlementLine).where(CODSettlementLine.settlement_id == st.id)):
        if line.order_id is None or line.match_status in ("duplicate_in_report", "already_settled"):
            continue
        rec = db.scalar(select(CODRecord).where(CODRecord.order_id == line.order_id).with_for_update())
        if rec is None or rec.status == "settled":
            continue
        rec.status, rec.settled_at, rec.settlement_id = "settled", now, st.id
        rec.collected_minor, rec.fee_minor = line.collected_minor, line.fee_minor
        settled += 1
    st.status, st.confirmed_at, st.confirmed_by_user_id = "confirmed", now, ctx.actor.id
    st.bank_reference = (bank_reference or "").strip()[:120] or None
    audit.record(
        db,
        action="fulfillment.settlement_confirmed",
        resource_type="cod_settlement",
        resource_id=st.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"reference": st.reference, "net_minor": st.net_minor, "orders_settled": settled},
    )
    return st


# ----------------------------------------------------------------------------- sources
def _minor(raw: str) -> int:
    cleaned = (
        raw.replace(",", "").replace("NPR", "").replace("Rs.", "").replace("Rs", "").replace("रु", "").strip()
    )
    if not cleaned:
        return 0
    value = Decimal(cleaned)
    if value < 0:
        raise InvalidOperation
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_file(content: bytes) -> list[SettlementLineData]:
    """A courier's statement exported as CSV (Excel 'Save as CSV'). Amounts in rupees."""
    try:
        text_ = content.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValidationFailed("Save the statement as CSV (UTF-8)", code="settlement_file_invalid") from e
    reader = csv.DictReader(io.StringIO(text_))
    headers = {h: h.strip().lower().replace(" ", "_").replace(".", "") for h in (reader.fieldnames or [])}
    norm = set(headers.values())
    tracking_col = next((c for c in TRACKING_COLS if c in norm), None)
    collected_col = next((c for c in COLLECTED_COLS if c in norm), None)
    fee_cols = [c for c in FEE_COLS if c in norm]
    if tracking_col is None or collected_col is None:
        raise ValidationFailed(
            "The file needs a tracking number column and a COD collected column",
            code="settlement_file_invalid",
            details={
                "missing": [
                    n
                    for n, c in (("tracking_number", tracking_col), ("cod_collected", collected_col))
                    if c is None
                ]
            },
        )
    out: list[SettlementLineData] = []
    errors: list[dict[str, Any]] = []
    for i, raw_row in enumerate(reader, start=2):  # row 1 is the header
        row = {headers.get(k, k): (v or "").strip() for k, v in raw_row.items() if k is not None}
        tracking = row.get(tracking_col, "")
        if not tracking and not any(row.values()):
            continue  # blank line
        if len(out) >= MAX_ROWS:
            raise ValidationFailed(code="settlement_file_too_large", details={"max_rows": MAX_ROWS})
        if not tracking:
            errors.append({"row": i, "field": "tracking_number", "reason": "missing"})
            continue
        try:
            collected = _minor(row.get(collected_col, ""))
            fee = sum(_minor(row.get(c, "")) for c in fee_cols)
        except (InvalidOperation, ValueError):
            errors.append({"row": i, "field": "amount", "reason": "not_a_number"})
            continue
        out.append(SettlementLineData(tracking, collected, fee))
    if errors:
        raise ValidationFailed(
            "Some rows couldn't be read", code="settlement_file_invalid", details={"rows": errors[:50]}
        )
    if not out:
        raise ValidationFailed("The file has no rows", code="settlement_file_invalid", details={"rows": []})
    return out


def import_file(
    db: Session, ctx: TenantContext, account_id: uuid.UUID, reference: str, content: bytes
) -> tuple[CODSettlement, bool]:
    a = couriers.get_account(db, ctx, account_id)
    lines = parse_file(content)
    st, created = import_report(
        db,
        a,
        SettlementReport(reference=reference.strip(), currency=_currency(db, ctx), lines=lines),
        "file_import",
        ctx.actor.id,
    )
    if created:
        _audit_import(db, ctx, st)
    return st, created


def record_cash(
    db: Session,
    ctx: TenantContext,
    account_id: uuid.UUID,
    shipment_ids: list[uuid.UUID],
    reference: str | None,
) -> CODSettlement:
    """Own rider / courier without statements: the seller records the cash they received."""
    a = couriers.get_account(db, ctx, account_id)
    if CourierCapability.MANUAL_UPDATES.value not in a.capabilities:
        raise Conflict("Import this courier's statement instead", code="courier_sends_statements")
    rows = list(
        db.scalars(select(Shipment).where(Shipment.id.in_(shipment_ids), Shipment.courier_account_id == a.id))
    )
    if len(rows) != len(set(shipment_ids)):
        raise NotFound(code="shipment_not_found")
    ref = (reference or "").strip() or f"cash-{utcnow():%Y%m%d-%H%M%S}"
    report = SettlementReport(
        reference=ref,
        currency=_currency(db, ctx),
        lines=[
            SettlementLineData(s.tracking_number or f"NIV-{s.id.hex[:10]}", s.cod_amount_minor) for s in rows
        ],
    )
    for s in rows:  # manual parcels may have no tracking number: give them a stable internal one
        if not s.tracking_number:
            s.tracking_number = f"NIV-{s.id.hex[:10]}"
    db.flush()
    st, created = import_report(db, a, report, "manual", ctx.actor.id)
    if not created:
        raise Conflict("A settlement with this reference already exists", code="settlement_reference_used")
    _audit_import(db, ctx, st)
    if st.issue_count:
        return st  # e.g. a parcel not marked delivered: the seller sees why
    return confirm(db, ctx, st.id, None)


def _currency(db: Session, ctx: TenantContext) -> str:
    from app.domains.merchants.models import Merchant

    m = db.get(Merchant, ctx.merchant_id)
    return m.currency if m else "NPR"


def _audit_import(db: Session, ctx: TenantContext, st: CODSettlement) -> None:
    audit.record(
        db,
        action="fulfillment.settlement_imported",
        resource_type="cod_settlement",
        resource_id=st.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={
            "reference": st.reference,
            "source": st.source,
            "lines": st.line_count,
            "issues": st.issue_count,
        },
    )


def sync_account(db: Session, a: CourierAccount) -> int:
    reports = couriers.adapter_for(a).fetch_cod_settlements(a.last_settlement_sync_at)
    n = 0
    for r in reports:
        _, created = import_report(db, a, r, "courier_api")
        n += int(created)
    a.last_settlement_sync_at = utcnow()
    return n


def sync_all(db: Session) -> dict[str, int]:
    """Worker: fetch statements from couriers that publish them."""
    accounts = db.scalars(
        select(CourierAccount)
        .where(
            CourierAccount.status == "connected",
            CourierAccount.capabilities.contains([CourierCapability.COD_SETTLEMENT_REPORTS.value]),
        )
        .execution_options(skip_tenant_filter=True)
    ).all()
    stats = {"accounts": 0, "imported": 0, "failed": 0}
    for a in accounts:
        bind_tenant(db, a.merchant_id)
        try:
            with db.begin_nested():
                stats["imported"] += sync_account(db, a)
            stats["accounts"] += 1
        except IntegrationError as e:
            stats["failed"] += 1
            log.warning("cod_settlement_sync_failed", provider=a.provider, error=e.code)
    return stats


# ----------------------------------------------------------------------------- dashboard (PAY-010)
def awaiting(
    db: Session, *, courier_account_id: uuid.UUID | None = None, limit: int = 200
) -> list[dict[str, Any]]:
    """Delivered COD parcels whose cash hasn't reached the merchant yet, oldest first."""
    stmt = (
        select(Shipment, Order.number, Order.ship_name, CourierAccount.display_name)
        .join(Order, Order.id == Shipment.order_id)
        .join(CODRecord, CODRecord.order_id == Shipment.order_id)
        .join(CourierAccount, CourierAccount.id == Shipment.courier_account_id)
        .where(Shipment.status == "delivered", Shipment.cod_amount_minor > 0, CODRecord.status != "settled")
        .order_by(Shipment.delivered_at.asc())
        .limit(limit)
    )
    if courier_account_id:
        stmt = stmt.where(Shipment.courier_account_id == courier_account_id)
    now = utcnow()
    return [
        {
            "shipment_id": s.id,
            "order_id": s.order_id,
            "order_number": number,
            "customer_name": name,
            "courier_account_id": s.courier_account_id,
            "courier_name": s.courier_name or courier,
            "tracking_number": s.tracking_number,
            "cod_amount": {"amount_minor": s.cod_amount_minor, "currency": s.currency},
            "delivered_at": s.delivered_at,
            "days_waiting": (now - s.delivered_at).days if s.delivered_at else None,
        }
        for s, number, name, courier in db.execute(stmt).all()
    ]


def overview(db: Session, ctx: TenantContext) -> dict[str, Any]:
    from app.domains.payments import service as payments

    summary = payments.cod_summary(db, ctx)
    now = utcnow()
    aging = {"d0_7": [0, 0], "d8_14": [0, 0], "d15_plus": [0, 0]}
    by_courier: dict[str, dict[str, Any]] = {}
    for row in awaiting(db, limit=5000):
        days = row["days_waiting"] or 0
        key = "d0_7" if days <= 7 else "d8_14" if days <= 14 else "d15_plus"
        amount = row["cod_amount"]["amount_minor"]
        aging[key][0] += 1
        aging[key][1] += amount
        c = by_courier.setdefault(
            str(row["courier_account_id"]),
            {
                "courier_account_id": row["courier_account_id"],
                "courier_name": row["courier_name"],
                "count": 0,
                "amount_minor": 0,
            },
        )
        c["count"] += 1
        c["amount_minor"] += amount
    review = db.scalar(
        select(func.count()).select_from(CODSettlement).where(CODSettlement.status == "needs_review")
    )
    last30 = db.execute(
        select(func.count(), func.coalesce(func.sum(CODSettlement.net_minor), 0)).where(
            CODSettlement.status == "confirmed", CODSettlement.confirmed_at >= now - timedelta(days=30)
        )
    ).one()
    return {
        **summary,
        "currency": _currency(db, ctx),
        "awaiting_by_age": {k: {"count": v[0], "amount_minor": v[1]} for k, v in aging.items()},
        "awaiting_by_courier": sorted(by_courier.values(), key=lambda c: -c["amount_minor"]),
        "settlements_needing_review": int(review or 0),
        "received_last_30_days": {"count": int(last30[0]), "amount_minor": int(last30[1])},
    }


# ----------------------------------------------------------------------------- views
def settlement_view(db: Session, st: CODSettlement, *, detail: bool = False) -> dict[str, Any]:
    a = db.get(CourierAccount, st.courier_account_id)
    out: dict[str, Any] = {
        "id": st.id,
        "courier_account_id": st.courier_account_id,
        "courier_name": a.display_name if a else st.provider,
        "provider": st.provider,
        "source": st.source,
        "reference": st.reference,
        "status": st.status,
        "currency": st.currency,
        "collected_minor": st.collected_minor,
        "fees_minor": st.fees_minor,
        "net_minor": st.net_minor,
        "expected_minor": st.expected_minor,
        "line_count": st.line_count,
        "issue_count": st.issue_count,
        "period_start": st.period_start,
        "period_end": st.period_end,
        "created_at": st.created_at,
        "confirmed_at": st.confirmed_at,
        "bank_reference": st.bank_reference,
    }
    if detail:
        rows = db.execute(
            select(CODSettlementLine, Order.number)
            .outerjoin(Order, Order.id == CODSettlementLine.order_id)
            .where(CODSettlementLine.settlement_id == st.id)
            .order_by(CODSettlementLine.id)
        ).all()
        out["lines"] = [
            {
                "id": ln.id,
                "tracking_number": ln.tracking_number,
                "shipment_id": ln.shipment_id,
                "order_id": ln.order_id,
                "order_number": number,
                "collected_minor": ln.collected_minor,
                "fee_minor": ln.fee_minor,
                "expected_minor": ln.expected_minor,
                "match_status": ln.match_status,
                "accepted": ln.accepted_at is not None,
                "accept_reason": ln.accept_reason,
                "note": ln.note,
            }
            for ln, number in rows
        ]
    return out
