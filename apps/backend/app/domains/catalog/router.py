from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.api.idempotent import run_idempotent
from app.core.context import TenantContext
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import build_page, paginate_desc
from app.domains.catalog import imports, service
from app.domains.catalog.models import Category, Collection, ImportJob, Product, Variant

router = APIRouter(prefix="/catalog", tags=["catalog"])

# Money is integer minor units, strictly: "100", 12.5 or true are rejected rather than coerced (QA-004).
Minor = Field(default=None, ge=0, le=10_000_000_000, strict=True)


# ----------------------------------------------------------------------------- schemas
class OptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    values: list[str] = Field(default_factory=list, max_length=50)


class VariantIn(BaseModel):
    options: dict[str, str] = Field(default_factory=dict)
    price_minor: int = Field(ge=0, le=10_000_000_000, strict=True)
    sku: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=32)
    compare_at_minor: int | None = Minor
    cost_minor: int | None = Minor
    weight_grams: int | None = Field(default=None, ge=0, le=1_000_000)
    length_mm: int | None = Field(default=None, ge=0, le=10_000)
    width_mm: int | None = Field(default=None, ge=0, le=10_000)
    height_mm: int | None = Field(default=None, ge=0, le=10_000)


class ProductIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    handle: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=20_000)
    title_ne: str | None = Field(default=None, max_length=255)
    description_ne: str | None = Field(default=None, max_length=20_000)
    category_id: uuid.UUID | None = None
    brand: str | None = Field(default=None, max_length=120)
    product_type: str | None = Field(default=None, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=30)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=320)
    options: list[OptionIn] = Field(default_factory=list, max_length=3)
    variants: list[VariantIn] = Field(min_length=1, max_length=100)


class ProductPatch(BaseModel):
    version: int | None = Field(default=None, description="Optimistic lock: last version you read")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    handle: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=20_000)
    title_ne: str | None = Field(default=None, max_length=255)
    description_ne: str | None = Field(default=None, max_length=20_000)
    category_id: uuid.UUID | None = None
    brand: str | None = Field(default=None, max_length=120)
    product_type: str | None = Field(default=None, max_length=120)
    tags: list[str] | None = Field(default=None, max_length=30)
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=320)
    final_sale: bool | None = None


class StatusIn(BaseModel):
    status: Literal["draft", "active", "archived"]
    version: int | None = None


class VariantPatch(BaseModel):
    version: int | None = Field(default=None, description="Optimistic lock: product version you last read")
    price_minor: int | None = Minor
    compare_at_minor: int | None = Minor
    cost_minor: int | None = Minor
    sku: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=32)
    weight_grams: int | None = Field(default=None, ge=0, le=1_000_000)
    length_mm: int | None = Field(default=None, ge=0, le=10_000)
    width_mm: int | None = Field(default=None, ge=0, le=10_000)
    height_mm: int | None = Field(default=None, ge=0, le=10_000)


class AttributeIn(BaseModel):
    key: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=500)
    locale: Literal["en", "ne"] = "en"


class AttributesIn(BaseModel):
    items: list[AttributeIn] = Field(min_length=1, max_length=50)


class ConfirmIn(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=50)


class MediaItemIn(BaseModel):
    asset_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    alt_text: str | None = Field(default=None, max_length=300)


class MediaIn(BaseModel):
    items: list[MediaItemIn] = Field(max_length=20)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    name_ne: str | None = Field(default=None, max_length=120)
    parent_id: uuid.UUID | None = None


class CollectionIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)


class CollectionProductsIn(BaseModel):
    product_ids: list[uuid.UUID] = Field(max_length=500)

    @field_validator("product_ids")
    @classmethod
    def _dedupe(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(v))


def _summary(p: Product, variants: list[Variant]) -> dict[str, Any]:
    prices = [v.price_minor for v in variants if v.status == "active"]
    return {
        "id": p.id,
        "title": p.title,
        "handle": p.handle,
        "status": p.status,
        "category_id": p.category_id,
        "version": p.version,
        "updated_at": p.updated_at,
        "variant_count": len([v for v in variants if v.status == "active"]),
        "price_range": {"min_minor": min(prices), "max_minor": max(prices), "currency": variants[0].currency}
        if prices
        else None,
    }


# ----------------------------------------------------------------------------- products
@router.get("/products")
def list_products(
    status: Literal["draft", "active", "archived"] | None = None,
    q: str | None = Query(None, max_length=100),
    category_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    stmt = select(Product)
    stmt = stmt.where(Product.status == status) if status else stmt.where(Product.status != "archived")
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        like = f"%{q.lower()}%"
        sku_match = select(Variant.product_id).where(Variant.sku.ilike(like))
        stmt = stmt.where(
            or_(Product.title.ilike(like), Product.handle.ilike(like), Product.id.in_(sku_match))
        )
    rows = list(db.scalars(paginate_desc(stmt, Product.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    variants: dict[uuid.UUID, list[Variant]] = {}
    if items:
        for v in db.scalars(select(Variant).where(Variant.product_id.in_([p.id for p in items]))):
            variants.setdefault(v.product_id, []).append(v)
    return {"items": [_summary(p, variants.get(p.id, [])) for p in items], "next_cursor": nxt}


@router.post("/products", status_code=201)
def create_product(
    body: ProductIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    def _do() -> dict[str, Any]:
        data = service.ProductInput(
            **body.model_dump(exclude={"options", "variants"}),
            options=[service.OptionInput(o.name, o.values) for o in body.options],
            variants=[service.VariantInput(**v.model_dump()) for v in body.variants],
        )
        p = service.create_product(db, ctx, data)
        return service.product_detail(db, ctx, p.id)

    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope="catalog.products.create",
        body=body.model_dump(mode="json"),
        status_code=201,
        fn=_do,
    )


@router.get("/products/{product_id}")
def get_product(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.product_detail(db, ctx, product_id)


@router.patch("/products/{product_id}")
def patch_product(
    product_id: uuid.UUID,
    body: ProductPatch,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True, exclude={"version"})
    service.update_product(db, ctx, product_id, body.version, fields)
    return service.product_detail(db, ctx, product_id)


@router.post("/products/{product_id}/status")
def set_status(
    product_id: uuid.UUID,
    body: StatusIn,
    ctx: TenantContext = Depends(require("catalog.publish")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.change_status(db, ctx, product_id, body.status, body.version)
    return service.product_detail(db, ctx, product_id)


class NewVariantIn(VariantIn):
    version: int | None = Field(default=None, description="Optimistic lock: last product version you read")


@router.post("/products/{product_id}/variants", status_code=201)
def add_variant(
    product_id: uuid.UUID,
    body: NewVariantIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.add_variant(
        db, ctx, product_id, body.version, service.VariantInput(**body.model_dump(exclude={"version"}))
    )
    return service.product_detail(db, ctx, product_id)


@router.patch("/products/{product_id}/variants/{variant_id}")
def patch_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    body: VariantPatch,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.update_variant(
        db,
        ctx,
        product_id,
        variant_id,
        body.model_dump(exclude_unset=True, exclude={"version"}),
        body.version,
    )
    return service.product_detail(db, ctx, product_id)


@router.delete("/products/{product_id}/variants/{variant_id}", status_code=204)
def archive_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    version: int | None = Query(None),
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.archive_variant(db, ctx, product_id, variant_id, version)
    return Response(status_code=204)


@router.put("/products/{product_id}/attributes")
def set_attributes(
    product_id: uuid.UUID,
    body: AttributesIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.set_attributes(
        db, ctx, product_id, [service.AttributeInput(**i.model_dump()) for i in body.items]
    )
    return service.product_detail(db, ctx, product_id)


@router.post("/products/{product_id}/attributes/confirm")
def confirm_attributes(
    product_id: uuid.UUID,
    body: ConfirmIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.confirm_attributes(db, ctx, product_id, body.keys)
    return service.product_detail(db, ctx, product_id)


@router.put("/products/{product_id}/media")
def set_media(
    product_id: uuid.UUID,
    body: MediaIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    service.set_product_media(db, ctx, product_id, [service.MediaInput(**i.model_dump()) for i in body.items])
    return service.product_detail(db, ctx, product_id)


# ----------------------------------------------------------------------------- categories / collections
@router.get("/categories")
def list_categories(
    ctx: TenantContext = Depends(require("catalog.read")), db: Session = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(Category).order_by(Category.path).limit(1000))
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "name_ne": c.name_ne,
                "parent_id": c.parent_id,
                "path": c.path,
                "depth": c.depth,
            }
            for c in rows
        ]
    }


@router.post("/categories", status_code=201)
def create_category(
    body: CategoryIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    c = service.create_category(db, ctx, body.name, body.parent_id, body.name_ne)
    return {
        "id": c.id,
        "name": c.name,
        "name_ne": c.name_ne,
        "parent_id": c.parent_id,
        "path": c.path,
        "depth": c.depth,
    }


@router.get("/collections")
def list_collections(
    ctx: TenantContext = Depends(require("catalog.read")), db: Session = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(Collection).order_by(Collection.title).limit(500))
    return {
        "items": [
            {"id": c.id, "title": c.title, "handle": c.handle, "description": c.description} for c in rows
        ]
    }


@router.post("/collections", status_code=201)
def create_collection(
    body: CollectionIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    c = service.create_collection(db, ctx, body.title, body.description)
    return {"id": c.id, "title": c.title, "handle": c.handle, "description": c.description}


@router.put("/collections/{collection_id}/products")
def set_collection_products(
    collection_id: uuid.UUID,
    body: CollectionProductsIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    return {"count": service.set_collection_products(db, ctx, collection_id, body.product_ids)}


# ----------------------------------------------------------------------------- imports
def _job(j: ImportJob) -> dict[str, Any]:
    return {
        "id": j.id,
        "status": j.status,
        "file_name": j.file_name,
        "total_rows": j.total_rows,
        "products_created": j.products_created,
        "products_updated": j.products_updated,
        "rows_failed": j.rows_failed,
        "errors": j.errors[:200],
        "created_at": j.created_at,
        "started_at": j.started_at,
        "finished_at": j.finished_at,
    }


@router.post("/imports", status_code=202)
def create_import(
    file: UploadFile,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    if file.content_type not in (
        "text/csv",
        "application/vnd.ms-excel",
        "application/csv",
        "text/plain",
        None,
    ):
        raise ValidationFailed("Upload a .csv file", code="unsupported_file_type")
    data = file.file.read(imports.MAX_BYTES + 1)
    job = imports.queue_import(db, ctx, file.filename or "import.csv", data)
    return _job(job)


@router.get("/imports/{import_id}")
def get_import(
    import_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    j = db.get(ImportJob, import_id)
    if j is None or j.merchant_id != ctx.merchant_id:
        raise NotFound()
    return _job(j)


@router.get("/imports")
def list_imports(
    ctx: TenantContext = Depends(require("catalog.read")), db: Session = Depends(get_db, scope="function")
) -> dict:
    rows = db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(50))
    return {"items": [{k: v for k, v in _job(j).items() if k != "errors"} for j in rows]}


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    name_ne: str | None = Field(default=None, max_length=120)
    parent_id: uuid.UUID | None = None
    move: bool = Field(default=False, description="true to change parent (parent_id null = make top-level)")


@router.patch("/categories/{category_id}")
def update_category(
    category_id: uuid.UUID,
    body: CategoryPatch,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    c = service.update_category(db, ctx, category_id, body.name, body.name_ne, body.parent_id, body.move)
    return {
        "id": c.id,
        "name": c.name,
        "name_ne": c.name_ne,
        "parent_id": c.parent_id,
        "path": c.path,
        "depth": c.depth,
    }


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.delete_category(db, ctx, category_id)
    return Response(status_code=204)


@router.get("/collections/{collection_id}/products")
def collection_products(
    collection_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return {"items": service.collection_products(db, ctx, collection_id)}


@router.put("/collections/{collection_id}/products/{product_id}", status_code=204)
def add_to_collection(
    collection_id: uuid.UUID,
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.add_to_collection(db, ctx, collection_id, product_id)
    return Response(status_code=204)


@router.delete("/collections/{collection_id}/products/{product_id}", status_code=204)
def remove_from_collection(
    collection_id: uuid.UUID,
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    service.remove_from_collection(db, ctx, collection_id, product_id)
    return Response(status_code=204)
