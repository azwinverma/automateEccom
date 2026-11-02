"""CSV bulk import (CAT-008).

Format (header names are case-insensitive; only ``title`` and ``price`` are required)::

    handle,title,description,category,brand,tags,option1_name,option1_value,option2_name,option2_value,
    option3_name,option3_value,sku,barcode,price,compare_at_price,cost,weight_grams

* Prices are in **rupees** as sellers write them ("1250", "1,250.50"); converted exactly to paisa.
* Rows sharing a ``handle`` (or, if blank, the same ``title``) become one product with variants.
* Existing handle → product fields are updated and variants matched **by SKU** are re-priced.
  New variants on existing products are reported as row errors (not silently created).
* Each product group commits or fails on its own (savepoint): partial success is normal and every
  failure is reported with its row number. The same file (sha256) cannot be imported twice.
"""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import Actor, RequestMeta, TenantContext
from app.core.db import bind_tenant, utcnow
from app.core.errors import AppError, Conflict, ValidationFailed
from app.domains.audit import service as audit
from app.domains.catalog import rules
from app.domains.catalog import service as catalog
from app.domains.catalog.models import Category, ImportJob, Product, Variant
from app.domains.integrations.storage import get_storage, tenant_key
from app.domains.platform import outbox
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
REQUIRED = ("title", "price")
KNOWN = {
    "handle",
    "title",
    "description",
    "category",
    "brand",
    "tags",
    "option1_name",
    "option1_value",
    "option2_name",
    "option2_value",
    "option3_name",
    "option3_value",
    "sku",
    "barcode",
    "price",
    "compare_at_price",
    "cost",
    "weight_grams",
}


def rupees_to_minor(raw: str, field: str) -> int | None:
    s = raw.strip().replace(",", "").replace("Rs.", "").replace("Rs", "").replace("रू", "").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"{field}: '{raw}' is not a number") from e
    if d < 0 or d.as_tuple().exponent < -2:  # type: ignore[operator]
        raise ValueError(f"{field}: use at most 2 decimal places")
    return int(d * 100)


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValidationFailed(
        "The file must be a UTF-8 CSV (Excel: Save As → CSV UTF-8)", code="invalid_csv_encoding"
    )


def parse(data: bytes) -> list[dict[str, str]]:
    text = _decode(data)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationFailed("The file has no header row", code="invalid_csv")
    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [h for h in REQUIRED if h not in headers]
    if missing:
        raise ValidationFailed(
            "Missing required columns", code="invalid_csv", details={"missing_columns": missing}
        )
    rows = []
    for raw in reader:
        rows.append({k.strip().lower(): (v or "").strip() for k, v in raw.items() if k})
        if len(rows) > MAX_ROWS:
            raise ValidationFailed(f"At most {MAX_ROWS} rows per file", code="too_many_rows")
    if not rows:
        raise ValidationFailed("The file has no product rows", code="empty_csv")
    return rows


# ----------------------------------------------------------------------------- queue
def queue_import(db: Session, ctx: TenantContext, file_name: str, data: bytes) -> ImportJob:
    if len(data) > MAX_BYTES:
        raise ValidationFailed("File is larger than 5 MB", code="file_too_large")
    parse(data)  # fail fast on structural problems; row-level problems are reported by the job
    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(
        select(ImportJob).where(ImportJob.merchant_id == ctx.merchant_id, ImportJob.file_sha256 == digest)
    )
    if existing is not None:
        raise Conflict(
            "This exact file was already imported",
            code="duplicate_import",
            details={"import_id": str(existing.id), "status": existing.status},
        )
    job_id = uuid.uuid4()
    key = tenant_key(str(ctx.merchant_id), "imports", f"{job_id}.csv")
    get_storage().put(key, data, "text/csv")
    job = ImportJob(
        id=job_id,
        merchant_id=ctx.merchant_id,
        file_name=file_name[:255],
        file_sha256=digest,
        object_key=key,
        created_by_user_id=ctx.actor.id,
    )
    db.add(job)
    db.flush()
    audit.record(
        db,
        action="catalog.import_queued",
        resource_type="import",
        resource_id=job.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"file_name": job.file_name},
    )
    outbox.publish(
        db,
        event_type="catalog.import_queued",
        aggregate_type="import",
        aggregate_id=job.id,
        merchant_id=ctx.merchant_id,
        payload={"import_id": str(job.id)},
    )
    return job


# ----------------------------------------------------------------------------- process
@dataclass
class _Group:
    key: str
    rows: list[tuple[int, dict[str, str]]]


def _group(rows: list[dict[str, str]]) -> list[_Group]:
    groups: dict[str, _Group] = {}
    for i, r in enumerate(rows, start=2):  # row 1 is the header; numbers match the spreadsheet
        key = r.get("handle") or rules.handleize(r.get("title", "")) or f"row-{i}"
        groups.setdefault(key, _Group(key, [])).rows.append((i, r))
    return list(groups.values())


def _category_id(
    db: Session, ctx: TenantContext, path_text: str, cache: dict[str, uuid.UUID]
) -> uuid.UUID | None:
    """'Clothing > Women > Kurta' → creates missing levels."""
    if not path_text:
        return None
    if path_text in cache:
        return cache[path_text]
    parent: uuid.UUID | None = None
    built = ""
    for name in [p.strip() for p in path_text.replace("/", ">").split(">") if p.strip()]:
        slug = rules.handleize(name)
        built = f"{built}/{slug}" if built else slug
        found = db.scalar(
            select(Category).where(Category.merchant_id == ctx.merchant_id, Category.path == built)
        )
        parent = found.id if found else catalog.create_category(db, ctx, name, parent).id
    assert parent is not None
    cache[path_text] = parent
    return parent


def _variant_input(i: int, r: dict[str, str], option_names: list[str]) -> catalog.VariantInput:
    opts = {}
    for n, slot in zip(option_names, (1, 2, 3), strict=False):
        val = r.get(f"option{slot}_value", "")
        if not val:
            raise ValueError(f"row {i}: missing value for option '{n}'")
        opts[n] = val
    price = rupees_to_minor(r.get("price", ""), "price")
    if price is None:
        raise ValueError("price is required")
    w = r.get("weight_grams", "")
    return catalog.VariantInput(
        options=opts,
        price_minor=price,
        sku=r.get("sku") or None,
        barcode=r.get("barcode") or None,
        compare_at_minor=rupees_to_minor(r.get("compare_at_price", ""), "compare_at_price"),
        cost_minor=rupees_to_minor(r.get("cost", ""), "cost"),
        weight_grams=int(w) if w.isdigit() else None,
    )


def _apply_group(db: Session, ctx: TenantContext, g: _Group, cache: dict[str, uuid.UUID]) -> str:
    first = g.rows[0][1]
    option_names = [first[f"option{n}_name"] for n in (1, 2, 3) if first.get(f"option{n}_name")]
    existing = None
    if first.get("handle"):
        existing = db.scalar(
            select(Product).where(Product.merchant_id == ctx.merchant_id, Product.handle == first["handle"])
        )
    if existing is None:
        variants = [_variant_input(i, r, option_names) for i, r in g.rows]
        catalog.create_product(
            db,
            ctx,
            catalog.ProductInput(
                title=first.get("title", ""),
                handle=first.get("handle") or None,
                description=first.get("description") or None,
                category_id=_category_id(db, ctx, first.get("category", ""), cache),
                brand=first.get("brand") or None,
                tags=[t for t in first.get("tags", "").split(",") if t.strip()],
                options=[catalog.OptionInput(n, []) for n in option_names],
                variants=variants,
            ),
        )
        return "created"
    fields: dict[str, Any] = {k: first[k] for k in ("title", "description", "brand") if first.get(k)}
    if first.get("tags"):
        fields["tags"] = [t for t in first["tags"].split(",") if t.strip()]
    if fields:
        catalog.update_product(db, ctx, existing.id, None, fields)
    for i, r in g.rows:
        sku = rules.normalize_sku(r.get("sku"))
        v = (
            db.scalar(select(Variant).where(Variant.product_id == existing.id, Variant.sku == sku))
            if sku
            else None
        )
        if v is None:
            raise ValueError(
                f"row {i}: SKU '{r.get('sku') or ''}' not found on existing product "
                f"'{existing.handle}' — add new variants in the app"
            )
        upd: dict[str, Any] = {"price_minor": rupees_to_minor(r["price"], "price")}
        for col, fld in (("compare_at_price", "compare_at_minor"), ("cost", "cost_minor")):
            if r.get(col):
                upd[fld] = rupees_to_minor(r[col], col)
        if r.get("barcode"):
            upd["barcode"] = r["barcode"]
        catalog.update_variant(db, ctx, existing.id, v.id, upd)
    return "updated"


def process(db: Session, job_id: uuid.UUID) -> ImportJob:
    job = db.scalar(
        select(ImportJob)
        .where(ImportJob.id == job_id)
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if job is None or job.status not in ("queued", "processing"):
        return job  # type: ignore[return-value]  # already finished: idempotent
    bind_tenant(db, job.merchant_id)
    actor = (
        Actor(type="user", id=job.created_by_user_id, display="CSV import")
        if job.created_by_user_id
        else Actor.system("csv-import")
    )
    from app.domains.merchants.models import Membership
    from app.domains.merchants.rbac import permissions_for

    role = (
        db.scalar(
            select(Membership.role).where(
                Membership.user_id == job.created_by_user_id,
                Membership.merchant_id == job.merchant_id,
                Membership.status == "active",
            )
        )
        or "staff"
    )
    ctx = TenantContext(
        merchant_id=job.merchant_id,
        actor=actor,
        role=role,
        permissions=permissions_for(role),
        meta=RequestMeta(source="worker"),
    )
    job.status, job.started_at = "processing", utcnow()
    try:
        rows = parse(get_storage().get(job.object_key))
    except (AppError, OSError) as e:
        job.status, job.finished_at = "failed", utcnow()
        job.errors = [{"row": None, "code": getattr(e, "code", "file_unreadable"), "message": str(e)[:300]}]
        return job
    job.total_rows = len(rows)
    errors: list[dict[str, object]] = []
    created = updated = 0
    cache: dict[str, uuid.UUID] = {}
    for g in _group(rows):
        sp = db.begin_nested()
        try:
            outcome = _apply_group(db, ctx, g, cache)
            sp.commit()
            created += outcome == "created"
            updated += outcome == "updated"
        except (AppError, ValueError) as e:
            sp.rollback()
            code = getattr(e, "code", "invalid_row")
            msg = getattr(e, "message", None) or str(e)
            details = getattr(e, "details", None) or {}
            for i, _ in g.rows:
                errors.append(
                    {"row": i, "handle": g.key, "code": code, "message": str(msg)[:300], "details": details}
                )
            if len(errors) > 1000:
                errors = errors[:1000]
    job.products_created, job.products_updated = created, updated
    job.rows_failed = len({e["row"] for e in errors})
    job.errors = errors
    job.status = "completed_with_errors" if errors else "completed"
    job.finished_at = utcnow()
    audit.record(
        db,
        action="catalog.import_finished",
        resource_type="import",
        resource_id=job.id,
        actor=actor,
        merchant_id=job.merchant_id,
        meta=ctx.meta,
        metadata={"created": created, "updated": updated, "rows_failed": job.rows_failed},
    )
    log.info(
        "catalog_import_finished",
        import_id=str(job.id),
        created=created,
        updated=updated,
        rows_failed=job.rows_failed,
    )
    return job


@handler("catalog.import_queued")
def _on_import_queued(db: Session, ev: OutboxEvent) -> None:
    process(db, uuid.UUID(ev.payload["import_id"]))
