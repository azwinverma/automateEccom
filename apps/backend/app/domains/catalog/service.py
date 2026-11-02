"""Catalog use cases (CAT-001..007, CAT-009). All writes: tenant-scoped, validated, audited, and
publish outbox events that channel/inventory sync will consume."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.context import TenantContext
from app.core.db import utcnow
from app.core.errors import Conflict, InvalidStateTransition, NotFound, ValidationFailed
from app.domains.audit import service as audit
from app.domains.billing.service import entitlements, register_gauge
from app.domains.catalog import rules
from app.domains.catalog.models import (
    Category,
    Collection,
    CollectionProduct,
    Product,
    ProductAttribute,
    ProductMedia,
    ProductOption,
    ProductOptionValue,
    Variant,
    VariantOptionValue,
    VariantSupplier,
)
from app.domains.merchants.models import Merchant
from app.domains.platform import outbox

MAX_OPTIONS = 3
MAX_VALUES_PER_OPTION = 50
MAX_VARIANTS = 100

# Allowed lifecycle transitions (CAT-007). Anything else → 422 invalid_state_transition.
TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"active", "archived"}),
    "active": frozenset({"draft", "archived"}),
    "archived": frozenset({"draft"}),
}


@register_gauge("products")
def product_count(db: Session, merchant_id: uuid.UUID) -> int:
    """Non-archived products count toward the plan's product limit."""
    return (
        db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.merchant_id == merchant_id, Product.status != "archived")
        )
        or 0
    )


# ----------------------------------------------------------------------------- inputs
@dataclass
class OptionInput:
    name: str
    values: list[str]


@dataclass
class VariantInput:
    options: dict[str, str] = field(default_factory=dict)
    price_minor: int = 0
    sku: str | None = None
    barcode: str | None = None
    compare_at_minor: int | None = None
    cost_minor: int | None = None
    weight_grams: int | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None


@dataclass
class ProductInput:
    title: str
    handle: str | None = None
    description: str | None = None
    title_ne: str | None = None
    description_ne: str | None = None
    category_id: uuid.UUID | None = None
    brand: str | None = None
    product_type: str | None = None
    tags: list[str] = field(default_factory=list)
    seo_title: str | None = None
    seo_description: str | None = None
    options: list[OptionInput] = field(default_factory=list)
    variants: list[VariantInput] = field(default_factory=list)


# ----------------------------------------------------------------------------- helpers
def _currency(db: Session, merchant_id: uuid.UUID) -> str:
    m = db.get(Merchant, merchant_id)
    assert m is not None
    return m.currency


def _get_product(db: Session, ctx: TenantContext, product_id: uuid.UUID) -> Product:
    p = db.get(Product, product_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        raise NotFound()
    return p


def _check_version(p: Product, expected: int | None) -> None:
    if expected is not None and p.version != expected:
        raise Conflict(
            "This product was changed by someone else. Reload to see the latest version.",
            code="version_conflict",
            details={"current_version": p.version},
        )


def _unique_handle(db: Session, merchant_id: uuid.UUID, base: str, exclude: uuid.UUID | None = None) -> str:
    base = base or f"product-{uuid.uuid4().hex[:6]}"
    handle, n = base, 1
    while True:
        stmt = select(Product.id).where(Product.merchant_id == merchant_id, Product.handle == handle)
        if exclude:
            stmt = stmt.where(Product.id != exclude)
        if db.scalar(stmt) is None:
            return handle
        n += 1
        handle = f"{base[:110]}-{n}"


def _existing_skus(db: Session, merchant_id: uuid.UUID) -> set[str]:
    rows = db.scalars(select(Variant.sku).where(Variant.merchant_id == merchant_id, Variant.sku.is_not(None)))
    return {s for s in rows if s is not None}


def _clean_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    for t in tags:
        t = t.strip().lower()[:60]
        if t and t not in out:
            out.append(t)
    if len(out) > 30:
        raise ValidationFailed("At most 30 tags", code="too_many_tags")
    return out


def _signature(option_names: list[str], options: dict[str, str]) -> str:
    return "|".join(f"{n.lower()}={options[n].strip().lower()}" for n in option_names) or "default"


def _validate_variant_money(v: VariantInput) -> None:
    rules.validate_money("price_minor", v.price_minor)
    rules.validate_money("cost_minor", v.cost_minor)
    rules.validate_money("compare_at_minor", v.compare_at_minor)
    if v.compare_at_minor is not None and v.compare_at_minor <= v.price_minor:
        raise ValidationFailed(
            "Compare-at price must be higher than the price",
            code="invalid_compare_at",
            details={"fields": [{"loc": ["body", "compare_at_minor"]}]},
        )


def _publish(
    db: Session, ctx: TenantContext, event_type: str, p: Product, extra: dict[str, Any] | None = None
) -> None:
    outbox.publish(
        db,
        event_type=event_type,
        aggregate_type="product",
        aggregate_id=p.id,
        merchant_id=ctx.merchant_id,
        payload={"product_id": str(p.id), **(extra or {})},
    )


# ----------------------------------------------------------------------------- categories
def create_category(
    db: Session, ctx: TenantContext, name: str, parent_id: uuid.UUID | None, name_ne: str | None = None
) -> Category:
    parent = None
    if parent_id:
        parent = db.get(Category, parent_id)
        if parent is None or parent.merchant_id != ctx.merchant_id:
            raise NotFound("Parent category not found", code="category_not_found")
    slug = rules.handleize(name) or f"cat-{uuid.uuid4().hex[:6]}"
    path = f"{parent.path}/{slug}" if parent else slug
    depth = (parent.depth + 1) if parent else 0
    if depth > 5:
        raise ValidationFailed("Categories can be at most 6 levels deep", code="category_too_deep")
    if db.scalar(select(Category.id).where(Category.merchant_id == ctx.merchant_id, Category.path == path)):
        raise Conflict("A category with this name already exists here", code="category_exists")
    c = Category(
        merchant_id=ctx.merchant_id,
        parent_id=parent_id,
        name=name.strip(),
        name_ne=name_ne,
        slug=slug,
        path=path,
        depth=depth,
    )
    db.add(c)
    db.flush()
    audit.record(
        db,
        action="catalog.category_created",
        resource_type="category",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"path": [None, path]},
    )
    return c


# ----------------------------------------------------------------------------- products
def create_product(db: Session, ctx: TenantContext, data: ProductInput) -> Product:
    entitlements.check_gauge(db, ctx.merchant_id, "products")
    title = data.title.strip()
    if not title:
        raise ValidationFailed("Title is required", code="title_required")
    if data.category_id:
        cat = db.get(Category, data.category_id)
        if cat is None or cat.merchant_id != ctx.merchant_id:
            raise NotFound("Category not found", code="category_not_found")
    handle = rules.validate_handle(data.handle) if data.handle else None
    if handle and db.scalar(
        select(Product.id).where(Product.merchant_id == ctx.merchant_id, Product.handle == handle)
    ):
        raise Conflict("Another product already uses this handle", code="handle_taken")
    handle = handle or _unique_handle(db, ctx.merchant_id, rules.handleize(title))

    p = Product(
        merchant_id=ctx.merchant_id,
        title=title,
        handle=handle,
        description=data.description,
        title_ne=data.title_ne,
        description_ne=data.description_ne,
        category_id=data.category_id,
        brand=data.brand,
        product_type=data.product_type,
        tags=_clean_tags(data.tags),
        seo_title=data.seo_title,
        seo_description=data.seo_description,
        created_by_user_id=ctx.actor.id,
    )
    db.add(p)
    db.flush()
    _replace_options_and_variants(db, ctx, p, data.options, data.variants)
    audit.record(
        db,
        action="catalog.product_created",
        resource_type="product",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"title": [None, p.title], "handle": [None, p.handle], "status": [None, p.status]},
    )
    _publish(db, ctx, "catalog.product_created", p)
    return p


def _replace_options_and_variants(
    db: Session, ctx: TenantContext, p: Product, options: list[OptionInput], variants: list[VariantInput]
) -> None:
    if len(options) > MAX_OPTIONS:
        raise ValidationFailed(
            "A product can have at most 3 options (e.g. Color, Size, Material)", code="too_many_options"
        )
    names = [o.name.strip() for o in options]
    if len({n.lower() for n in names}) != len(names) or any(not n for n in names):
        raise ValidationFailed("Option names must be unique and non-empty", code="invalid_options")
    if not variants:
        raise ValidationFailed("Add at least one variant with a price", code="variant_required")
    if len(variants) > MAX_VARIANTS:
        raise ValidationFailed(f"At most {MAX_VARIANTS} variants per product", code="too_many_variants")
    if not options and len(variants) > 1:
        raise ValidationFailed("Multiple variants need options (e.g. Size)", code="options_required")

    # Collect values: declared + any used by variants (seller may type values directly on variants).
    values: dict[str, list[str]] = {n: [] for n in names}
    for o, n in zip(options, names, strict=True):
        for v in o.values:
            v = v.strip()
            if v and v.lower() not in {x.lower() for x in values[n]}:
                values[n].append(v)
    for vi in variants:
        missing = [n for n in names if not vi.options.get(n, "").strip()]
        extra = [k for k in vi.options if k not in names]
        if missing or extra:
            raise ValidationFailed(
                "Each variant needs exactly one value for every option",
                code="variant_options_mismatch",
                details={"missing": missing, "unknown": extra},
            )
        for n in names:
            v = vi.options[n].strip()
            if v.lower() not in {x.lower() for x in values[n]}:
                values[n].append(v)
    for n in names:
        if len(values[n]) > MAX_VALUES_PER_OPTION:
            raise ValidationFailed("Too many values for one option", code="too_many_option_values")

    value_ids: dict[tuple[str, str], uuid.UUID] = {}
    for pos, n in enumerate(names):
        opt = ProductOption(merchant_id=ctx.merchant_id, product_id=p.id, name=n, position=pos)
        db.add(opt)
        db.flush()
        for vpos, v in enumerate(values[n]):
            ov = ProductOptionValue(merchant_id=ctx.merchant_id, option_id=opt.id, value=v, position=vpos)
            db.add(ov)
            db.flush()
            value_ids[(n, v.lower())] = ov.id

    currency = _currency(db, ctx.merchant_id)
    existing = _existing_skus(db, ctx.merchant_id)
    seen_sigs: set[str] = set()
    for pos, vi in enumerate(variants):
        _validate_variant_money(vi)
        sig = _signature(names, vi.options)
        if sig in seen_sigs:
            raise ValidationFailed(
                "Two variants have the same option values",
                code="duplicate_variant",
                details={"options": vi.options},
            )
        seen_sigs.add(sig)
        canonical = [next(x for x in values[n] if x.lower() == vi.options[n].strip().lower()) for n in names]
        sku = rules.normalize_sku(vi.sku) or rules.generate_sku(p.handle, canonical, existing)
        if sku in existing and vi.sku:
            raise Conflict(
                f"SKU {sku} is already used by another product", code="sku_taken", details={"sku": sku}
            )
        existing.add(sku)
        var = Variant(
            merchant_id=ctx.merchant_id,
            product_id=p.id,
            sku=sku,
            barcode=rules.normalize_barcode(vi.barcode),
            title=" / ".join(canonical) or "Default",
            option_signature=sig,
            price_minor=vi.price_minor,
            compare_at_minor=vi.compare_at_minor,
            cost_minor=vi.cost_minor,
            currency=currency,
            weight_grams=vi.weight_grams,
            length_mm=vi.length_mm,
            width_mm=vi.width_mm,
            height_mm=vi.height_mm,
            position=pos,
        )
        db.add(var)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError as e:
            raise Conflict(
                "SKU or barcode already used by another product",
                code="sku_or_barcode_taken",
                details={"sku": sku, "barcode": var.barcode},
            ) from e
        for n in names:
            db.add(
                VariantOptionValue(
                    merchant_id=ctx.merchant_id,
                    variant_id=var.id,
                    option_value_id=value_ids[(n, vi.options[n].strip().lower())],
                )
            )
    db.flush()


UPDATABLE_FIELDS = (
    "title",
    "title_ne",
    "description",
    "description_ne",
    "category_id",
    "brand",
    "product_type",
    "tags",
    "seo_title",
    "seo_description",
    "handle",
)


def update_product(
    db: Session,
    ctx: TenantContext,
    product_id: uuid.UUID,
    expected_version: int | None,
    fields: dict[str, Any],
) -> Product:
    p = _get_product(db, ctx, product_id)
    _check_version(p, expected_version)
    before = {k: getattr(p, k) for k in fields if k in UPDATABLE_FIELDS}
    for k, v in fields.items():
        if k not in UPDATABLE_FIELDS:
            continue
        if k == "title":
            v = (v or "").strip()
            if not v:
                raise ValidationFailed("Title is required", code="title_required")
        if k == "handle" and v is not None:
            v = rules.validate_handle(v)
            if _unique_handle(db, ctx.merchant_id, v, exclude=p.id) != v:
                raise Conflict("Another product already uses this handle", code="handle_taken")
        if k == "tags":
            v = _clean_tags(v or [])
        if k == "category_id" and v is not None:
            cat = db.get(Category, v)
            if cat is None or cat.merchant_id != ctx.merchant_id:
                raise NotFound("Category not found", code="category_not_found")
        setattr(p, k, v)
    changes = audit.diff(
        {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in before.items()},
        {k: (str(getattr(p, k)) if isinstance(getattr(p, k), uuid.UUID) else getattr(p, k)) for k in before},
    )
    if not changes:
        return p
    try:
        db.flush()
    except StaleDataError as e:
        raise Conflict(
            "This product was changed by someone else. Reload to see the latest version.",
            code="version_conflict",
        ) from e
    audit.record(
        db,
        action="catalog.product_updated",
        resource_type="product",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes=changes,
    )
    _publish(db, ctx, "catalog.product_updated", p, {"fields": sorted(changes)})
    return p


def change_status(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, to: str, expected_version: int | None
) -> Product:
    p = _get_product(db, ctx, product_id)
    _check_version(p, expected_version)
    if to == p.status:
        return p
    if to not in TRANSITIONS.get(p.status, frozenset()):
        raise InvalidStateTransition(
            details={"from": p.status, "to": to, "allowed": sorted(TRANSITIONS.get(p.status, frozenset()))}
        )
    if to == "active":
        _assert_publishable(db, p)
    if p.status == "archived":
        entitlements.check_gauge(db, ctx.merchant_id, "products")
    old = p.status
    p.status = to
    now = utcnow()
    if to == "active" and p.published_at is None:
        p.published_at = now
    p.archived_at = now if to == "archived" else None
    try:
        db.flush()
    except StaleDataError as e:
        raise Conflict("This product was changed by someone else.", code="version_conflict") from e
    audit.record(
        db,
        action="catalog.product_status_changed",
        resource_type="product",
        resource_id=p.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"status": [old, to]},
    )
    _publish(db, ctx, "catalog.product_status_changed", p, {"from": old, "to": to})
    return p


def _assert_publishable(db: Session, p: Product) -> None:
    problems: list[str] = []
    if not p.title.strip():
        problems.append("title_required")
    variants = db.scalars(select(Variant).where(Variant.product_id == p.id, Variant.status == "active")).all()
    if not variants:
        problems.append("active_variant_required")
    if any(v.price_minor <= 0 for v in variants):
        problems.append("price_required")
    unconfirmed = db.scalar(
        select(func.count())
        .select_from(ProductAttribute)
        .where(ProductAttribute.product_id == p.id, ProductAttribute.confirmed.is_(False))
    )
    if unconfirmed:
        problems.append("unconfirmed_ai_attributes")
    if problems:
        raise ValidationFailed(
            "This product isn't ready to go live yet", code="not_publishable", details={"problems": problems}
        )


# ----------------------------------------------------------------------------- variants
VARIANT_FIELDS = (
    "price_minor",
    "compare_at_minor",
    "cost_minor",
    "sku",
    "barcode",
    "weight_grams",
    "length_mm",
    "width_mm",
    "height_mm",
)


def update_variant(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, variant_id: uuid.UUID, fields: dict[str, Any]
) -> Variant:
    p = _get_product(db, ctx, product_id)
    v = db.get(Variant, variant_id)
    if v is None or v.product_id != p.id:
        raise NotFound()
    before = {k: getattr(v, k) for k in fields if k in VARIANT_FIELDS}
    for k, val in fields.items():
        if k not in VARIANT_FIELDS:
            continue
        if k == "sku":
            val = rules.normalize_sku(val) or v.sku
        elif k == "barcode":
            val = rules.normalize_barcode(val)
        elif k.endswith("_minor"):
            rules.validate_money(k, val)
        setattr(v, k, val)
    if v.compare_at_minor is not None and v.compare_at_minor <= v.price_minor:
        raise ValidationFailed("Compare-at price must be higher than the price", code="invalid_compare_at")
    if p.status == "active" and v.price_minor <= 0:
        raise ValidationFailed("Live products need a price above zero", code="price_required")
    changes = audit.diff(before, {k: getattr(v, k) for k in before})
    if not changes:
        return v
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as e:
        raise Conflict("SKU or barcode already used by another product", code="sku_or_barcode_taken") from e
    p.updated_at = utcnow()  # bump product version so concurrent product editors see a conflict
    db.flush()
    audit.record(
        db,
        action="catalog.variant_updated",
        resource_type="variant",
        resource_id=v.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes=changes,
        metadata={"product_id": str(p.id)},
    )
    _publish(db, ctx, "catalog.variant_updated", p, {"variant_id": str(v.id), "fields": sorted(changes)})
    return v


def archive_variant(db: Session, ctx: TenantContext, product_id: uuid.UUID, variant_id: uuid.UUID) -> None:
    p = _get_product(db, ctx, product_id)
    v = db.get(Variant, variant_id)
    if v is None or v.product_id != p.id:
        raise NotFound()
    if v.status == "archived":
        return
    active = (
        db.scalar(
            select(func.count())
            .select_from(Variant)
            .where(Variant.product_id == p.id, Variant.status == "active")
        )
        or 0
    )
    if p.status == "active" and active <= 1:
        raise Conflict("A live product needs at least one variant. Unpublish it first.", code="last_variant")
    v.status = "archived"
    p.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        action="catalog.variant_archived",
        resource_type="variant",
        resource_id=v.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"product_id": str(p.id)},
    )
    _publish(db, ctx, "catalog.variant_updated", p, {"variant_id": str(v.id), "fields": ["status"]})


# ----------------------------------------------------------------------------- attributes
@dataclass
class AttributeInput:
    key: str
    value: str
    locale: str = "en"


def set_attributes(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, items: list[AttributeInput]
) -> list[ProductAttribute]:
    """Seller-entered attributes replace values for the same key/locale and are always confirmed."""
    p = _get_product(db, ctx, product_id)
    out = []
    for it in items:
        key = rules.handleize(it.key).replace("-", "_")[:60]
        if not key or not it.value.strip():
            raise ValidationFailed("Attribute key and value are required", code="invalid_attribute")
        row = db.scalar(
            select(ProductAttribute).where(
                ProductAttribute.product_id == p.id,
                ProductAttribute.key == key,
                ProductAttribute.locale == it.locale,
            )
        )
        old = row.value if row else None
        if row is None:
            row = ProductAttribute(
                merchant_id=ctx.merchant_id,
                product_id=p.id,
                key=key,
                locale=it.locale,
                value=it.value.strip()[:500],
            )
            db.add(row)
        else:
            row.value = it.value.strip()[:500]
        row.source, row.confidence, row.confirmed = "seller", None, True
        out.append(row)
        if old != row.value:
            audit.record(
                db,
                action="catalog.attribute_set",
                resource_type="product",
                resource_id=p.id,
                actor=ctx.actor,
                merchant_id=ctx.merchant_id,
                meta=ctx.meta,
                changes={key: [old, row.value]},
            )
    db.flush()
    return out


def suggest_attributes(
    db: Session,
    merchant_id: uuid.UUID,
    product_id: uuid.UUID,
    items: list[tuple[str, str, float]],
    locale: str = "en",
) -> int:
    """AI suggestions (from the Product Studio). Never overwrite seller-confirmed values; stay
    unconfirmed so the product cannot go live until the seller reviews them."""
    n = 0
    for key, value, confidence in items:
        row = db.scalar(
            select(ProductAttribute).where(
                ProductAttribute.product_id == product_id,
                ProductAttribute.key == key,
                ProductAttribute.locale == locale,
            )
        )
        if row is not None and row.source == "seller":
            continue
        if row is None:
            row = ProductAttribute(
                merchant_id=merchant_id, product_id=product_id, key=key, locale=locale, value=value
            )
            db.add(row)
        row.value, row.source, row.confidence, row.confirmed = value[:500], "ai", confidence, False
        n += 1
    db.flush()
    return n


def confirm_attributes(db: Session, ctx: TenantContext, product_id: uuid.UUID, keys: list[str]) -> int:
    p = _get_product(db, ctx, product_id)
    rows = db.scalars(
        select(ProductAttribute).where(
            ProductAttribute.product_id == p.id,
            ProductAttribute.key.in_(keys),
            ProductAttribute.confirmed.is_(False),
        )
    ).all()
    for r in rows:
        r.confirmed = True
    if rows:
        audit.record(
            db,
            action="catalog.attributes_confirmed",
            resource_type="product",
            resource_id=p.id,
            actor=ctx.actor,
            merchant_id=ctx.merchant_id,
            meta=ctx.meta,
            metadata={"keys": sorted(r.key for r in rows)},
        )
    return len(rows)


# ----------------------------------------------------------------------------- media
@dataclass
class MediaInput:
    asset_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    alt_text: str | None = None


MAX_PRODUCT_MEDIA = 20


def set_product_media(
    db: Session, ctx: TenantContext, product_id: uuid.UUID, items: list[MediaInput]
) -> None:
    """Replace the ordered photo list. Only processed (ready) photos of this merchant are accepted."""
    from app.domains.media.models import MediaAsset

    p = _get_product(db, ctx, product_id)
    if len(items) > MAX_PRODUCT_MEDIA:
        raise ValidationFailed(f"At most {MAX_PRODUCT_MEDIA} photos per product", code="too_many_media")
    ids = [i.asset_id for i in items]
    if len(set(ids)) != len(ids):
        raise ValidationFailed("The same photo is listed twice", code="duplicate_media")
    assets = {
        a.id: a
        for a in db.scalars(
            select(MediaAsset).where(MediaAsset.merchant_id == ctx.merchant_id, MediaAsset.id.in_(ids))
        )
    }
    missing = [str(i) for i in ids if i not in assets]
    if missing:
        raise NotFound("Some photos were not found", code="media_not_found", details={"asset_ids": missing})
    not_ready = [str(i) for i in ids if assets[i].status != "ready"]
    if not_ready:
        raise Conflict(
            "Some photos are still processing or were rejected",
            code="media_not_ready",
            details={"asset_ids": not_ready},
        )
    variant_ids = set(db.scalars(select(Variant.id).where(Variant.product_id == p.id)))
    bad_variants = [str(i.variant_id) for i in items if i.variant_id and i.variant_id not in variant_ids]
    if bad_variants:
        raise ValidationFailed(
            "Photo is linked to a variant of another product",
            code="invalid_variant",
            details={"variant_ids": bad_variants},
        )
    current = db.scalars(
        select(ProductMedia).where(ProductMedia.product_id == p.id).order_by(ProductMedia.position)
    ).all()
    before = [str(r.asset_id) for r in current]
    for row in current:
        db.delete(row)
    db.flush()
    for pos, it in enumerate(items):
        db.add(
            ProductMedia(
                merchant_id=ctx.merchant_id,
                product_id=p.id,
                asset_id=it.asset_id,
                variant_id=it.variant_id,
                position=pos,
                alt_text=(it.alt_text or "")[:300] or None,
            )
        )
    p.updated_at = utcnow()
    db.flush()
    after = [str(i) for i in ids]
    if before != after:
        audit.record(
            db,
            action="catalog.product_media_set",
            resource_type="product",
            resource_id=p.id,
            actor=ctx.actor,
            merchant_id=ctx.merchant_id,
            meta=ctx.meta,
            changes={"media": [before, after]},
        )
        _publish(db, ctx, "catalog.product_updated", p, {"fields": ["media"]})


def _media_views(db: Session, product_id: uuid.UUID) -> list[dict[str, Any]]:
    from app.domains.media.models import MediaAsset
    from app.domains.media.service import asset_view

    rows = db.execute(
        select(ProductMedia, MediaAsset)
        .join(MediaAsset, MediaAsset.id == ProductMedia.asset_id)
        .where(ProductMedia.product_id == product_id)
        .order_by(ProductMedia.position)
    ).all()
    out = []
    for pm, asset in rows:
        view = asset_view(db, asset)
        out.append(
            {
                "asset_id": asset.id,
                "position": pm.position,
                "variant_id": pm.variant_id,
                "alt_text": pm.alt_text,
                "quality_flags": view["quality_flags"],
                "source": view["source"],
                "thumb": view["derivatives"].get("thumb"),
                "medium": view["derivatives"].get("medium"),
            }
        )
    return out


# ----------------------------------------------------------------------------- collections
def create_collection(db: Session, ctx: TenantContext, title: str, description: str | None) -> Collection:
    handle = rules.handleize(title) or f"collection-{uuid.uuid4().hex[:6]}"
    if db.scalar(
        select(Collection.id).where(Collection.merchant_id == ctx.merchant_id, Collection.handle == handle)
    ):
        raise Conflict("A collection with this name already exists", code="collection_exists")
    c = Collection(merchant_id=ctx.merchant_id, title=title.strip(), handle=handle, description=description)
    db.add(c)
    db.flush()
    audit.record(
        db,
        action="catalog.collection_created",
        resource_type="collection",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes={"title": [None, c.title]},
    )
    return c


def set_collection_products(
    db: Session, ctx: TenantContext, collection_id: uuid.UUID, product_ids: list[uuid.UUID]
) -> int:
    c = db.get(Collection, collection_id)
    if c is None or c.merchant_id != ctx.merchant_id:
        raise NotFound()
    found = set(
        db.scalars(
            select(Product.id).where(Product.merchant_id == ctx.merchant_id, Product.id.in_(product_ids))
        )
    )
    missing = [str(i) for i in product_ids if i not in found]
    if missing:
        raise NotFound(
            "Some products were not found", code="product_not_found", details={"product_ids": missing}
        )
    for row in db.scalars(select(CollectionProduct).where(CollectionProduct.collection_id == c.id)):
        db.delete(row)
    db.flush()
    for pos, pid in enumerate(dict.fromkeys(product_ids)):
        db.add(
            CollectionProduct(merchant_id=ctx.merchant_id, collection_id=c.id, product_id=pid, position=pos)
        )
    db.flush()
    audit.record(
        db,
        action="catalog.collection_products_set",
        resource_type="collection",
        resource_id=c.id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        metadata={"count": len(found)},
    )
    return len(found)


# ----------------------------------------------------------------------------- reads
def product_detail(db: Session, ctx: TenantContext, product_id: uuid.UUID) -> dict[str, Any]:
    p = _get_product(db, ctx, product_id)
    options = db.scalars(
        select(ProductOption).where(ProductOption.product_id == p.id).order_by(ProductOption.position)
    ).all()
    opt_by_id = {o.id: o for o in options}
    values = (
        db.scalars(
            select(ProductOptionValue)
            .where(ProductOptionValue.option_id.in_([o.id for o in options]))
            .order_by(ProductOptionValue.position)
        ).all()
        if options
        else []
    )
    val_by_id = {v.id: v for v in values}
    variants = db.scalars(select(Variant).where(Variant.product_id == p.id).order_by(Variant.position)).all()
    links = (
        db.scalars(
            select(VariantOptionValue).where(VariantOptionValue.variant_id.in_([v.id for v in variants]))
        ).all()
        if variants
        else []
    )
    var_opts: dict[uuid.UUID, dict[str, str]] = {}
    for link in links:
        ov = val_by_id[link.option_value_id]
        var_opts.setdefault(link.variant_id, {})[opt_by_id[ov.option_id].name] = ov.value
    suppliers = (
        db.scalars(
            select(VariantSupplier).where(VariantSupplier.variant_id.in_([v.id for v in variants]))
        ).all()
        if variants
        else []
    )
    attrs = db.scalars(
        select(ProductAttribute).where(ProductAttribute.product_id == p.id).order_by(ProductAttribute.key)
    ).all()
    collections = list(
        db.scalars(select(CollectionProduct.collection_id).where(CollectionProduct.product_id == p.id))
    )
    media = _media_views(db, p.id)
    return {
        "id": p.id,
        "title": p.title,
        "title_ne": p.title_ne,
        "handle": p.handle,
        "description": p.description,
        "description_ne": p.description_ne,
        "status": p.status,
        "kind": p.kind,
        "category_id": p.category_id,
        "brand": p.brand,
        "product_type": p.product_type,
        "tags": p.tags,
        "seo_title": p.seo_title,
        "seo_description": p.seo_description,
        "version": p.version,
        "published_at": p.published_at,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "options": [
            {"id": o.id, "name": o.name, "values": [v.value for v in values if v.option_id == o.id]}
            for o in options
        ],
        "variants": [
            {
                "id": v.id,
                "title": v.title,
                "sku": v.sku,
                "barcode": v.barcode,
                "options": var_opts.get(v.id, {}),
                "price": {"amount_minor": v.price_minor, "currency": v.currency},
                "compare_at": {"amount_minor": v.compare_at_minor, "currency": v.currency}
                if v.compare_at_minor
                else None,
                "cost": {"amount_minor": v.cost_minor, "currency": v.currency}
                if v.cost_minor is not None
                else None,
                "weight_grams": v.weight_grams,
                "dimensions_mm": [v.length_mm, v.width_mm, v.height_mm],
                "status": v.status,
                "suppliers": [
                    {
                        "supplier_id": s.supplier_id,
                        "supplier_sku": s.supplier_sku,
                        "cost_minor": s.cost_minor,
                        "moq": s.moq,
                        "lead_time_days": s.lead_time_days,
                    }
                    for s in suppliers
                    if s.variant_id == v.id
                ],
            }
            for v in variants
        ],
        "attributes": [
            {
                "key": a.key,
                "value": a.value,
                "locale": a.locale,
                "source": a.source,
                "confidence": a.confidence,
                "confirmed": a.confirmed,
            }
            for a in attrs
        ],
        "collection_ids": collections,
        "media": media,
        "needs_review": any(not a.confirmed for a in attrs),
    }
