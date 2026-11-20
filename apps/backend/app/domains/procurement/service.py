"""Procurement service (PRO-001…006).

Approval (PRO-004, spec 06 "PO above threshold" is R3): a PO whose total is above the shop's `po_minor`
threshold always waits for an explicit approval by someone with procurement.approve, even if that person
created it. Below the threshold, a PO submitted by an approver is approved on submit; one submitted by
someone without procurement.approve waits for an approver.

Receiving (PRO-005): partial deliveries are separate receipts (lots). Good units go into stock through the
inventory ledger (reference purchase_receipt); defective units are recorded but never stocked.

Landed cost (PRO-006): freight + duty + other are allocated to lines by ordered value. A unit's landed cost
= its purchase price + its share. The variant's cost becomes the moving average of what's on hand and what
arrived at landed cost, so profit (order-line cost snapshots) uses true cost from then on.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.context import TenantContext
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from app.domains.audit import service as audit
from app.domains.catalog.models import Product, Supplier, Variant, VariantSupplier
from app.domains.procurement.models import (
    OPEN_PO_STATUSES,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
)

SUPPLIER_FIELDS = (
    "name",
    "phone",
    "email",
    "contact_name",
    "address",
    "default_lead_time_days",
    "payment_terms",
    "notes",
)


def _audit(db: Session, ctx: TenantContext, action: str, rtype: str, rid: Any, **meta: Any) -> None:
    audit.record(
        db,
        action=f"procurement.{action}",
        resource_type=rtype,
        resource_id=rid,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata=meta,
    )


# ----------------------------------------------------------------------------- suppliers (PRO-001)
def get_supplier(db: Session, ctx: TenantContext, supplier_id: uuid.UUID) -> Supplier:
    s = db.get(Supplier, supplier_id)
    if s is None or s.merchant_id != ctx.merchant_id:
        raise NotFound(code="supplier_not_found")
    return s


def create_supplier(db: Session, ctx: TenantContext, data: dict[str, Any]) -> Supplier:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationFailed("Enter the supplier's name", code="supplier_name_required")
    dup = db.scalar(select(Supplier.id).where(func.lower(Supplier.name) == name.lower()))
    if dup:
        raise Conflict("A supplier with this name already exists", code="supplier_exists")
    s = Supplier(merchant_id=ctx.merchant_id, **{k: data.get(k) for k in SUPPLIER_FIELDS}, status="active")
    s.name = name
    db.add(s)
    db.flush()
    _audit(db, ctx, "supplier_created", "supplier", s.id, name=name)
    return s


def update_supplier(
    db: Session, ctx: TenantContext, supplier_id: uuid.UUID, data: dict[str, Any]
) -> Supplier:
    s = get_supplier(db, ctx, supplier_id)
    before = {k: getattr(s, k) for k in data}
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise ValidationFailed("Enter the supplier's name", code="supplier_name_required")
        dup = db.scalar(
            select(Supplier.id).where(func.lower(Supplier.name) == name.lower(), Supplier.id != s.id)
        )
        if dup:
            raise Conflict("A supplier with this name already exists", code="supplier_exists")
        data["name"] = name
    for k, v in data.items():
        if k in (*SUPPLIER_FIELDS, "status"):
            setattr(s, k, v)
    _audit(db, ctx, "supplier_updated", "supplier", s.id, before={k: str(v) for k, v in before.items()})
    return s


def supplier_view(s: Supplier) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "status": s.status,
        **{k: getattr(s, k) for k in SUPPLIER_FIELDS},
    }


# ----------------------------------------------------------------------------- supplier products (PRO-002)
def _variant(db: Session, ctx: TenantContext, variant_id: uuid.UUID) -> Variant:
    v = db.get(Variant, variant_id)
    if v is None or v.merchant_id != ctx.merchant_id:
        raise NotFound(code="variant_not_found")
    return v


def set_supplier_product(
    db: Session, ctx: TenantContext, supplier_id: uuid.UUID, variant_id: uuid.UUID, data: dict[str, Any]
) -> VariantSupplier:
    s = get_supplier(db, ctx, supplier_id)
    v = _variant(db, ctx, variant_id)
    row = db.get(VariantSupplier, (v.id, s.id))
    if row is None:
        row = VariantSupplier(merchant_id=ctx.merchant_id, variant_id=v.id, supplier_id=s.id)
        db.add(row)
        if not db.scalar(select(VariantSupplier.supplier_id).where(VariantSupplier.variant_id == v.id)):
            row.is_preferred = True  # the first supplier for a variant is its preferred one
    for k in ("supplier_sku", "cost_minor", "moq", "lead_time_days"):
        if k in data:
            setattr(row, k, data[k])
    if data.get("is_preferred"):
        _set_preferred(db, v.id, s.id)
        row.is_preferred = True
    db.flush()
    _audit(
        db,
        ctx,
        "supplier_product_set",
        "supplier",
        s.id,
        variant_id=str(v.id),
        **{k: data[k] for k in data if k != "is_preferred"},
    )
    return row


def _set_preferred(db: Session, variant_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    for r in db.scalars(select(VariantSupplier).where(VariantSupplier.variant_id == variant_id)):
        r.is_preferred = r.supplier_id == supplier_id


def set_preferred(db: Session, ctx: TenantContext, variant_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    v = _variant(db, ctx, variant_id)
    if db.get(VariantSupplier, (v.id, supplier_id)) is None:
        raise NotFound(code="supplier_product_not_found")
    _set_preferred(db, v.id, supplier_id)
    _audit(db, ctx, "preferred_supplier_set", "variant", v.id, supplier_id=str(supplier_id))


def remove_supplier_product(
    db: Session, ctx: TenantContext, supplier_id: uuid.UUID, variant_id: uuid.UUID
) -> None:
    get_supplier(db, ctx, supplier_id)
    row = db.get(VariantSupplier, (variant_id, supplier_id))
    if row is None or row.merchant_id != ctx.merchant_id:
        raise NotFound(code="supplier_product_not_found")
    db.delete(row)
    _audit(db, ctx, "supplier_product_removed", "supplier", supplier_id, variant_id=str(variant_id))


def supplier_products(db: Session, merchant_id: uuid.UUID, supplier_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        select(VariantSupplier, Variant, Product)
        .join(Variant, Variant.id == VariantSupplier.variant_id)
        .join(Product, Product.id == Variant.product_id)
        .where(VariantSupplier.supplier_id == supplier_id, VariantSupplier.merchant_id == merchant_id)
        .order_by(Product.title, Variant.title)
    ).all()
    return [
        {
            "variant_id": str(v.id),
            "product_id": str(p.id),
            "title": p.title,
            "variant": None if v.title == "Default" else v.title,
            "sku": v.sku,
            "supplier_sku": vs.supplier_sku,
            "cost_minor": vs.cost_minor,
            "moq": vs.moq,
            "lead_time_days": vs.lead_time_days,
            "is_preferred": vs.is_preferred,
            "current_cost_minor": v.cost_minor,
            "price_minor": v.price_minor,
        }
        for vs, v, p in rows
    ]


# ----------------------------------------------------------------------------- purchase orders (PRO-003)
def _next_number(db: Session, merchant_id: uuid.UUID) -> str:
    key = int.from_bytes(hashlib.sha256(f"po_number:{merchant_id}".encode()).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
    n = (
        db.scalar(
            select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.merchant_id == merchant_id)
        )
        or 0
    )
    return f"PO-{1001 + n}"


def get_po(db: Session, ctx: TenantContext, po_id: uuid.UUID, *, lock: bool = False) -> PurchaseOrder:
    stmt = select(PurchaseOrder).where(PurchaseOrder.id == po_id)
    if lock:
        stmt = stmt.with_for_update()
    po = db.scalar(stmt)
    if po is None or po.merchant_id != ctx.merchant_id:
        raise NotFound(code="purchase_order_not_found")
    return po


def _lines(db: Session, po_id: uuid.UUID) -> list[PurchaseOrderLine]:
    return list(
        db.scalars(
            select(PurchaseOrderLine).where(PurchaseOrderLine.po_id == po_id).order_by(PurchaseOrderLine.id)
        )
    )


def _set_lines(db: Session, ctx: TenantContext, po: PurchaseOrder, lines: list[dict[str, Any]]) -> None:
    if not lines:
        raise ValidationFailed("Add at least one item", code="po_lines_required")
    seen: set[uuid.UUID] = set()
    for old in _lines(db, po.id):
        db.delete(old)
    db.flush()
    subtotal = 0
    for ln in lines:
        v = _variant(db, ctx, ln["variant_id"])
        if v.id in seen:
            raise ValidationFailed("Each item can appear once", code="po_duplicate_line")
        seen.add(v.id)
        qty = int(ln["quantity"])
        if qty <= 0:
            raise ValidationFailed("Quantity must be positive", code="quantity_invalid")
        cost = ln.get("unit_cost_minor")
        if cost is None:
            vs = db.get(VariantSupplier, (v.id, po.supplier_id))
            cost = vs.cost_minor if vs and vs.cost_minor is not None else v.cost_minor
        if cost is None:
            raise ValidationFailed(
                "Enter the purchase price", code="po_cost_required", details={"variant_id": str(v.id)}
            )
        db.add(
            PurchaseOrderLine(
                merchant_id=ctx.merchant_id,
                po_id=po.id,
                variant_id=v.id,
                quantity=qty,
                unit_cost_minor=int(cost),
            )
        )
        subtotal += qty * int(cost)
    po.subtotal_minor = subtotal
    db.flush()


def create_po(
    db: Session, ctx: TenantContext, data: dict[str, Any], *, idempotency_key: str, source: str = "seller"
) -> PurchaseOrder:
    from app.domains.merchants.models import Merchant

    existing = db.scalar(select(PurchaseOrder).where(PurchaseOrder.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    s = get_supplier(db, ctx, data["supplier_id"])
    if s.status != "active":
        raise Conflict("This supplier is archived", code="supplier_archived")
    m = db.get(Merchant, ctx.merchant_id)
    po = PurchaseOrder(
        merchant_id=ctx.merchant_id,
        number=_next_number(db, ctx.merchant_id),
        supplier_id=s.id,
        location_id=data.get("location_id"),
        source=source,
        currency=m.currency if m else "NPR",
        freight_minor=int(data.get("freight_minor") or 0),
        duty_minor=int(data.get("duty_minor") or 0),
        other_minor=int(data.get("other_minor") or 0),
        expected_at=data.get("expected_at"),
        notes=data.get("notes"),
        idempotency_key=idempotency_key,
        recommendation_id=data.get("recommendation_id"),
        created_by_user_id=ctx.actor.id,
    )
    db.add(po)
    db.flush()
    _set_lines(db, ctx, po, data["lines"])
    _audit(
        db,
        ctx,
        "po_created",
        "purchase_order",
        po.id,
        number=po.number,
        total_minor=po.total_minor,
        source=source,
    )
    return po


def update_po(
    db: Session, ctx: TenantContext, po_id: uuid.UUID, version: int | None, data: dict[str, Any]
) -> PurchaseOrder:
    po = get_po(db, ctx, po_id, lock=True)
    if version is not None and version != po.version:
        raise Conflict(
            "Someone else changed this order",
            code="version_conflict",
            details={"current_version": po.version},
        )
    if po.status != "draft":
        raise Conflict("Only drafts can be edited", code="po_not_draft")
    for k in ("freight_minor", "duty_minor", "other_minor"):
        if k in data and data[k] is not None:
            setattr(po, k, int(data[k]))
    for k in ("expected_at", "notes", "location_id"):
        if k in data:
            setattr(po, k, data[k])
    if data.get("lines") is not None:
        _set_lines(db, ctx, po, data["lines"])
    po.updated_at = utcnow()
    db.flush()
    _audit(db, ctx, "po_updated", "purchase_order", po.id, total_minor=po.total_minor)
    return po


def add_line(
    db: Session,
    ctx: TenantContext,
    po: PurchaseOrder,
    variant_id: uuid.UUID,
    quantity: int,
    unit_cost: int | None,
) -> None:
    """Used by reorder suggestions to merge into an open draft for the same supplier."""
    current: list[dict[str, Any]] = [
        {"variant_id": ln.variant_id, "quantity": ln.quantity, "unit_cost_minor": ln.unit_cost_minor}
        for ln in _lines(db, po.id)
    ]
    for c in current:
        if c["variant_id"] == variant_id:
            c["quantity"] = max(c["quantity"], quantity)
            break
    else:
        current.append({"variant_id": variant_id, "quantity": quantity, "unit_cost_minor": unit_cost})
    _set_lines(db, ctx, po, current)


def submit(db: Session, ctx: TenantContext, po_id: uuid.UUID) -> PurchaseOrder:
    from app.domains.automation import policy

    po = get_po(db, ctx, po_id, lock=True)
    if po.status != "draft":
        raise Conflict("Only drafts can be submitted", code="po_not_draft")
    limit = policy.threshold(policy.settings(db, ctx.merchant_id), "po_minor")
    po.submitted_at = utcnow()
    if po.total_minor > limit:
        po.status, po.approval_reason = "pending_approval", "above_threshold"
    elif ctx.has("procurement.approve"):
        po.status, po.approval_reason = "approved", None
        po.approved_by_user_id, po.approved_at = ctx.actor.id, utcnow()
    else:
        po.status, po.approval_reason = "pending_approval", "needs_approver"
    _audit(
        db,
        ctx,
        "po_submitted",
        "purchase_order",
        po.id,
        status=po.status,
        total_minor=po.total_minor,
        limit_minor=limit,
    )
    return po


def approve(db: Session, ctx: TenantContext, po_id: uuid.UUID) -> PurchaseOrder:
    if not ctx.has("procurement.approve"):
        raise PermissionDenied(
            "Only an owner or manager can approve purchase orders", code="permission_denied"
        )
    po = get_po(db, ctx, po_id, lock=True)
    if po.status == "approved":
        return po
    if po.status != "pending_approval":
        raise Conflict("This order isn't waiting for approval", code="po_not_pending")
    po.status, po.approved_by_user_id, po.approved_at = "approved", ctx.actor.id, utcnow()
    _audit(
        db, ctx, "po_approved", "purchase_order", po.id, total_minor=po.total_minor, reason=po.approval_reason
    )
    return po


def reject(db: Session, ctx: TenantContext, po_id: uuid.UUID, reason: str) -> PurchaseOrder:
    if not ctx.has("procurement.approve"):
        raise PermissionDenied(
            "Only an owner or manager can reject purchase orders", code="permission_denied"
        )
    po = get_po(db, ctx, po_id, lock=True)
    if po.status != "pending_approval":
        raise Conflict("This order isn't waiting for approval", code="po_not_pending")
    po.status, po.notes = "draft", ((po.notes or "") + f"\nReturned for changes: {reason}").strip()[:1000]
    _audit(db, ctx, "po_rejected", "purchase_order", po.id, reason=reason[:300])
    return po


def mark_sent(db: Session, ctx: TenantContext, po_id: uuid.UUID) -> PurchaseOrder:
    po = get_po(db, ctx, po_id, lock=True)
    if po.status == "sent":
        return po
    if po.status != "approved":
        raise Conflict("Approve the order before sending it", code="po_not_approved")
    po.status, po.sent_at = "sent", utcnow()
    _audit(db, ctx, "po_sent", "purchase_order", po.id)
    return po


def cancel(db: Session, ctx: TenantContext, po_id: uuid.UUID, reason: str) -> PurchaseOrder:
    po = get_po(db, ctx, po_id, lock=True)
    if po.status not in OPEN_PO_STATUSES:
        raise Conflict("This order is closed", code="po_closed")
    received = any(ln.received_quantity for ln in _lines(db, po.id))
    # Something already arrived: close the order (the rest won't come) instead of cancelling it.
    po.status = "received" if received else "cancelled"
    po.cancelled_at, po.cancel_reason = utcnow(), reason[:300]
    if received:
        po.received_at = po.received_at or utcnow()
    _audit(db, ctx, "po_closed" if received else "po_cancelled", "purchase_order", po.id, reason=reason[:300])
    return po


# ----------------------------------------------------------------------------- receiving + landed cost
def landed_unit_costs(po: PurchaseOrder, lines: list[PurchaseOrderLine]) -> dict[uuid.UUID, int]:
    extras = po.freight_minor + po.duty_minor + po.other_minor
    value = sum(ln.unit_cost_minor * ln.quantity for ln in lines)
    out = {}
    for ln in lines:
        share = (ln.unit_cost_minor * ln.quantity / value) if value else (1 / len(lines))
        out[ln.id] = round(ln.unit_cost_minor + extras * share / ln.quantity)
    return out


def receive(
    db: Session,
    ctx: TenantContext,
    po_id: uuid.UUID,
    items: list[dict[str, Any]],
    *,
    idempotency_key: str,
    lot_code: str | None = None,
    note: str | None = None,
) -> PurchaseReceipt:
    from app.domains.inventory import service as inventory
    from app.domains.inventory.models import InventoryLevel

    existing = db.scalar(select(PurchaseReceipt).where(PurchaseReceipt.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    po = get_po(db, ctx, po_id, lock=True)
    if po.status not in ("approved", "sent", "partially_received"):
        raise Conflict(
            "This order can't be received now", code="po_not_receivable", details={"status": po.status}
        )
    lines = {ln.id: ln for ln in _lines(db, po.id)}
    if not items or not any(
        (int(i.get("quantity") or 0) + int(i.get("defective_quantity") or 0)) > 0 for i in items
    ):
        raise ValidationFailed("Enter what arrived", code="receipt_empty")
    landed = landed_unit_costs(po, list(lines.values()))
    n_receipts = (
        db.scalar(select(func.count()).select_from(PurchaseReceipt).where(PurchaseReceipt.po_id == po.id))
        or 0
    )
    r = PurchaseReceipt(
        merchant_id=ctx.merchant_id,
        po_id=po.id,
        supplier_id=po.supplier_id,
        lot_code=(lot_code or f"{po.number}-{n_receipts + 1}").strip()[:40],
        note=note,
        idempotency_key=idempotency_key,
        received_by_user_id=ctx.actor.id,
    )
    db.add(r)
    db.flush()
    for i in items:
        ln = lines.get(uuid.UUID(str(i["po_line_id"])))
        if ln is None:
            raise NotFound(code="po_line_not_found")
        good, bad = int(i.get("quantity") or 0), int(i.get("defective_quantity") or 0)
        if good < 0 or bad < 0:
            raise ValidationFailed("Quantities can't be negative", code="quantity_invalid")
        if good + bad == 0:
            continue
        if ln.received_quantity + good + bad > ln.quantity:
            raise ValidationFailed(
                "More than was ordered",
                code="receipt_over_order",
                details={"po_line_id": str(ln.id), "remaining": ln.quantity - ln.received_quantity},
            )
        ln.received_quantity += good + bad
        ln.defective_quantity += bad
        db.add(
            PurchaseReceiptLine(
                merchant_id=ctx.merchant_id,
                receipt_id=r.id,
                po_line_id=ln.id,
                variant_id=ln.variant_id,
                quantity=good,
                defective_quantity=bad,
                unit_cost_minor=ln.unit_cost_minor,
                landed_unit_cost_minor=landed[ln.id],
            )
        )
        if good:
            v = db.get(Variant, ln.variant_id)
            assert v is not None
            on_hand_before = int(
                db.scalar(
                    select(func.coalesce(func.sum(InventoryLevel.on_hand), 0)).where(
                        InventoryLevel.variant_id == v.id
                    )
                )
                or 0
            )
            old = v.cost_minor
            inventory.receive(
                db,
                ctx,
                v.id,
                good,
                location_id=po.location_id,
                reason=f"{po.number} ({r.lot_code})",
                key=f"po-receipt:{r.id}:{ln.id}",
            )
            v.cost_minor = (
                landed[ln.id]
                if old is None or on_hand_before <= 0
                else round((on_hand_before * old + good * landed[ln.id]) / (on_hand_before + good))
            )
            if old != v.cost_minor:
                _audit(
                    db,
                    ctx,
                    "variant_cost_updated",
                    "variant",
                    v.id,
                    before=old,
                    after=v.cost_minor,
                    landed_unit_cost_minor=landed[ln.id],
                    lot=r.lot_code,
                )
            vs = db.get(VariantSupplier, (v.id, po.supplier_id))
            if vs is None:
                vs = VariantSupplier(merchant_id=ctx.merchant_id, variant_id=v.id, supplier_id=po.supplier_id)
                vs.is_preferred = not db.scalar(
                    select(VariantSupplier.supplier_id).where(VariantSupplier.variant_id == v.id)
                )
                db.add(vs)
            vs.cost_minor = ln.unit_cost_minor  # last purchase price from this supplier
    db.flush()
    po.sent_at = po.sent_at or po.approved_at or utcnow()
    done = all(ln.received_quantity >= ln.quantity for ln in lines.values())
    po.status = "received" if done else "partially_received"
    if done:
        po.received_at = utcnow()
    _audit(db, ctx, "po_received", "purchase_order", po.id, lot=r.lot_code, complete=done)
    return r


def incoming(db: Session, merchant_id: uuid.UUID, variant_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Units on approved/sent/partly received orders that haven't arrived yet."""
    if not variant_ids:
        return {}
    rows = db.execute(
        select(
            PurchaseOrderLine.variant_id,
            func.sum(PurchaseOrderLine.quantity - PurchaseOrderLine.received_quantity),
        )
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.po_id)
        .where(
            PurchaseOrder.merchant_id == merchant_id,
            PurchaseOrder.status.in_(("approved", "sent", "partially_received")),
            PurchaseOrderLine.variant_id.in_(variant_ids),
        )
        .group_by(PurchaseOrderLine.variant_id)
    ).all()
    return {vid: int(q or 0) for vid, q in rows}


# ----------------------------------------------------------------------------- views
def po_view(db: Session, po: PurchaseOrder) -> dict[str, Any]:
    lines = _lines(db, po.id)
    landed = landed_unit_costs(po, lines) if lines else {}
    s = db.get(Supplier, po.supplier_id)
    out_lines = []
    warnings = []
    for ln in lines:
        v = db.get(Variant, ln.variant_id)
        p = db.get(Product, v.product_id) if v else None
        vs = db.get(VariantSupplier, (ln.variant_id, po.supplier_id))
        if vs and vs.moq and ln.quantity < vs.moq:
            warnings.append({"code": "below_moq", "variant_id": str(ln.variant_id), "moq": vs.moq})
        out_lines.append(
            {
                "id": str(ln.id),
                "variant_id": str(ln.variant_id),
                "product_id": str(p.id) if p else None,
                "title": p.title if p else None,
                "variant": None if v is None or v.title == "Default" else v.title,
                "sku": v.sku if v else None,
                "quantity": ln.quantity,
                "unit_cost_minor": ln.unit_cost_minor,
                "landed_unit_cost_minor": landed.get(ln.id),
                "received_quantity": ln.received_quantity,
                "defective_quantity": ln.defective_quantity,
                "remaining": ln.quantity - ln.received_quantity,
            }
        )
    receipts = [
        {
            "id": str(r.id),
            "lot_code": r.lot_code,
            "received_at": r.received_at.isoformat(),
            "note": r.note,
            "lines": [
                {
                    "po_line_id": str(rl.po_line_id),
                    "variant_id": str(rl.variant_id),
                    "quantity": rl.quantity,
                    "defective_quantity": rl.defective_quantity,
                    "landed_unit_cost_minor": rl.landed_unit_cost_minor,
                }
                for rl in db.scalars(
                    select(PurchaseReceiptLine).where(PurchaseReceiptLine.receipt_id == r.id)
                )
            ],
        }
        for r in db.scalars(
            select(PurchaseReceipt)
            .where(PurchaseReceipt.po_id == po.id)
            .order_by(PurchaseReceipt.received_at)
        )
    ]
    return {
        "id": str(po.id),
        "number": po.number,
        "status": po.status,
        "source": po.source,
        "supplier": {
            "id": str(po.supplier_id),
            "name": s.name if s else None,
            "phone": s.phone if s else None,
        },
        "location_id": str(po.location_id) if po.location_id else None,
        "currency": po.currency,
        "subtotal_minor": po.subtotal_minor,
        "freight_minor": po.freight_minor,
        "duty_minor": po.duty_minor,
        "other_minor": po.other_minor,
        "total_minor": po.total_minor,
        "expected_at": po.expected_at.isoformat() if po.expected_at else None,
        "notes": po.notes,
        "approval_reason": po.approval_reason,
        "submitted_at": _iso(po.submitted_at),
        "approved_at": _iso(po.approved_at),
        "sent_at": _iso(po.sent_at),
        "received_at": _iso(po.received_at),
        "cancelled_at": _iso(po.cancelled_at),
        "cancel_reason": po.cancel_reason,
        "recommendation_id": str(po.recommendation_id) if po.recommendation_id else None,
        "version": po.version,
        "created_at": po.created_at.isoformat(),
        "lines": out_lines,
        "receipts": receipts,
        "warnings": warnings,
        "share_text": share_text(po, s, out_lines),
    }


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def share_text(po: PurchaseOrder, s: Supplier | None, lines: list[dict[str, Any]]) -> str:
    """A plain message the seller can paste into WhatsApp/Viber/email (no prices invented, no extras)."""
    rows = [
        f"- {ln['title'] or ''}{' (' + ln['variant'] + ')' if ln['variant'] else ''}"
        f"{' [' + ln['sku'] + ']' if ln['sku'] else ''}: {ln['quantity']}"
        for ln in lines
    ]
    when = f"\nNeeded by: {po.expected_at.date().isoformat()}" if po.expected_at else ""
    return f"Purchase order {po.number}\nTo: {s.name if s else ''}\n" + "\n".join(rows) + when
