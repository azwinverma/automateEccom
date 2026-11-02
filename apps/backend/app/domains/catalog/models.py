"""Universal catalog (CAT-001..010).

Design rules:
* Relational, not JSON: options, option values, variant↔value links, attributes and supplier links
  are rows with constraints, because inventory, orders and channel listings join on them.
* Money is integer minor units in the merchant currency (NPR paisa). Never floats.
* ``Product.version`` is an optimistic-lock counter: concurrent staff edits fail with 409 instead
  of silently overwriting each other.
* Attributes record provenance (seller / ai / import / channel) and AI confidence so AI never
  silently becomes the source of truth for commercial facts.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TenantScoped, TimestampMixin

PRODUCT_STATUSES = ("draft", "active", "archived")


class Category(IdMixin, TimestampMixin, TenantScoped, Base):
    """Merchant taxonomy node. ``path`` is the materialised slug path (``clothing/women/kurta``)."""

    __tablename__ = "catalog_categories"
    __table_args__ = (
        UniqueConstraint("merchant_id", "path"),
        CheckConstraint("depth between 0 and 5", name="depth"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_categories.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_ne: Mapped[str | None] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Supplier(IdMixin, TimestampMixin, TenantScoped, Base):
    """Minimal supplier reference; procurement (PRO-001) extends it."""

    __tablename__ = "catalog_suppliers"
    __table_args__ = (Index("uq_supplier_name", "merchant_id", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(String(1000))


class Product(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "catalog_products"
    __table_args__ = (
        UniqueConstraint("merchant_id", "handle"),
        CheckConstraint("status in ('draft','active','archived')", name="status"),
        CheckConstraint("kind in ('simple','bundle')", name="kind"),
        Index("ix_products_merchant_status", "merchant_id", "status", "id"),
        Index("ix_products_title_lower", text("lower(title)")),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ne: Mapped[str | None] = mapped_column(String(255))
    handle: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    description_ne: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="simple", nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_categories.id", ondelete="SET NULL")
    )
    brand: Mapped[str | None] = mapped_column(String(120))
    product_type: Mapped[str | None] = mapped_column(String(120))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list, nullable=False)
    seo_title: Mapped[str | None] = mapped_column(String(70))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    published_at: Mapped[datetime | None]
    archived_at: Mapped[datetime | None]
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class ProductOption(IdMixin, TenantScoped, Base):
    __tablename__ = "catalog_product_options"
    __table_args__ = (
        UniqueConstraint("product_id", "name"),
        CheckConstraint("position between 0 and 2", name="max_three_options"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductOptionValue(IdMixin, TenantScoped, Base):
    __tablename__ = "catalog_product_option_values"
    __table_args__ = (UniqueConstraint("option_id", "value"),)

    option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_product_options.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Variant(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "catalog_variants"
    __table_args__ = (
        Index("uq_variants_sku", "merchant_id", "sku", unique=True, postgresql_where=text("sku is not null")),
        Index(
            "uq_variants_barcode",
            "merchant_id",
            "barcode",
            unique=True,
            postgresql_where=text("barcode is not null"),
        ),
        # One variant per option combination within a product.
        UniqueConstraint("product_id", "option_signature"),
        CheckConstraint("price_minor >= 0", name="price_nonneg"),
        CheckConstraint("cost_minor is null or cost_minor >= 0", name="cost_nonneg"),
        CheckConstraint(
            "compare_at_minor is null or compare_at_minor > price_minor", name="compare_at_gt_price"
        ),
        CheckConstraint("weight_grams is null or weight_grams between 0 and 1000000", name="weight"),
        CheckConstraint("status in ('active','archived')", name="status"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str | None] = mapped_column(String(64))
    barcode: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # "Red / M", or "Default"
    option_signature: Mapped[str] = mapped_column(String(300), nullable=False)  # stable key of option values
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    compare_at_minor: Mapped[int | None] = mapped_column(BigInteger)
    cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    weight_grams: Mapped[int | None] = mapped_column(Integer)
    length_mm: Mapped[int | None] = mapped_column(Integer)
    width_mm: Mapped[int | None] = mapped_column(Integer)
    height_mm: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)


class VariantOptionValue(TenantScoped, Base):
    __tablename__ = "catalog_variant_option_values"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="CASCADE"), primary_key=True
    )
    option_value_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_product_option_values.id", ondelete="RESTRICT"), primary_key=True
    )


class ProductAttribute(IdMixin, TimestampMixin, TenantScoped, Base):
    """Structured attribute (material, fit, neckline...). AI-suggested values carry confidence and
    stay ``confirmed = false`` until the seller confirms them."""

    __tablename__ = "catalog_product_attributes"
    __table_args__ = (
        UniqueConstraint("product_id", "key", "locale"),
        CheckConstraint("source in ('seller','ai','import','channel')", name="source"),
        CheckConstraint("confidence is null or (confidence >= 0 and confidence <= 1)", name="confidence"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), default="en", nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="seller", nullable=False)
    confidence: Mapped[float | None]
    confirmed: Mapped[bool] = mapped_column(default=True, nullable=False)


class Collection(IdMixin, TimestampMixin, TenantScoped, Base):
    __tablename__ = "catalog_collections"
    __table_args__ = (UniqueConstraint("merchant_id", "handle"),)

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    handle: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class CollectionProduct(TenantScoped, Base):
    __tablename__ = "catalog_collection_products"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_collections.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_products.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BundleComponent(TenantScoped, Base):
    """Bundle extension: a bundle product's variant is made of component variants."""

    __tablename__ = "catalog_bundle_components"
    __table_args__ = (
        CheckConstraint("quantity between 1 and 100", name="qty"),
        CheckConstraint("bundle_variant_id <> component_variant_id", name="not_self"),
    )

    bundle_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="CASCADE"), primary_key=True
    )
    component_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="RESTRICT"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class VariantSupplier(TenantScoped, Base):
    __tablename__ = "catalog_variant_suppliers"
    __table_args__ = (
        CheckConstraint("cost_minor is null or cost_minor >= 0", name="cost"),
        CheckConstraint("moq is null or moq >= 1", name="moq"),
        CheckConstraint("lead_time_days is null or lead_time_days between 0 and 365", name="lead"),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_variants.id", ondelete="CASCADE"), primary_key=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_suppliers.id", ondelete="RESTRICT"), primary_key=True
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(80))
    cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    moq: Mapped[int | None] = mapped_column(Integer)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    is_preferred: Mapped[bool] = mapped_column(default=False, nullable=False)


class ImportJob(IdMixin, TimestampMixin, TenantScoped, Base):
    """CSV bulk import (CAT-008). Processed by a worker; per-row errors are stored for download."""

    __tablename__ = "catalog_import_jobs"
    __table_args__ = (
        UniqueConstraint("merchant_id", "file_sha256"),
        CheckConstraint(
            "status in ('queued','processing','completed','completed_with_errors','failed')", name="status"
        ),
    )

    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    products_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    products_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
