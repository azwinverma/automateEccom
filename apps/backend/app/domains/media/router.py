from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.config import Environment, get_settings
from app.core.context import TenantContext
from app.core.errors import NotFound, PermissionDenied
from app.core.pagination import build_page, paginate_desc
from app.domains.integrations.storage import LocalStorage, get_storage
from app.domains.media import service
from app.domains.media.models import MediaAsset

router = APIRouter(prefix="/media", tags=["media"])
dev_router = APIRouter(tags=["dev"], include_in_schema=False)


class UploadIn(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=64)
    size_bytes: int = Field(gt=0)
    purpose: Literal["product", "content", "brand", "other"] = "product"


@router.post("/uploads", status_code=201)
def create_upload(
    body: UploadIn, ctx: TenantContext = Depends(require("media.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    a, upload = service.create_upload(
        db, ctx, body.file_name, body.content_type, body.size_bytes, body.purpose
    )
    return {"asset_id": a.id, "upload": upload}


@router.post("/{asset_id}/complete", status_code=202)
def complete_upload(
    asset_id: uuid.UUID, ctx: TenantContext = Depends(require("media.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.asset_view(db, service.complete_upload(db, ctx, asset_id), with_urls=False)


@router.get("/{asset_id}")
def get_asset(
    asset_id: uuid.UUID, ctx: TenantContext = Depends(require("media.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.asset_view(db, service._get(db, ctx, asset_id))


@router.get("")
def list_assets(
    status: Literal["ready", "processing", "rejected"] | None = None,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
    ctx: TenantContext = Depends(require("media.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(MediaAsset).where(MediaAsset.status.not_in(("deleted", "pending_upload")))
    if status:
        stmt = stmt.where(MediaAsset.status == status)
    rows = list(db.scalars(paginate_desc(stmt, MediaAsset.id, limit, cursor)))
    items, nxt = build_page(rows, limit)
    return {"items": [service.asset_view(db, a) for a in items], "next_cursor": nxt}


@router.delete("/{asset_id}", status_code=204)
def delete_asset(
    asset_id: uuid.UUID, ctx: TenantContext = Depends(require("media.write")), db: Session = Depends(get_db)
) -> Response:
    service.delete_asset(db, ctx, asset_id)
    return Response(status_code=204)


# ----------------------------------------------------------------------------- dev object store
def _local() -> LocalStorage:
    s = get_settings()
    st = get_storage()
    if s.environment in (Environment.PRODUCTION, Environment.STAGING) or not isinstance(st, LocalStorage):
        raise NotFound()
    return st


@dev_router.put("/_dev/objects/{key:path}", status_code=200)
async def dev_put(key: str, request: Request, exp: int = Query(...), sig: str = Query(...)) -> Response:
    st = _local()
    if not st.verify("PUT", key, exp, sig):
        raise PermissionDenied("Invalid or expired upload URL", code="invalid_signature")
    data = await request.body()
    if len(data) > get_settings().media_max_upload_bytes:
        raise PermissionDenied("Too large", code="file_too_large")
    st.put(key, data, request.headers.get("content-type", "application/octet-stream"))
    return Response(status_code=200)


@dev_router.get("/_dev/objects/{key:path}")
def dev_get(key: str, exp: int = Query(...), sig: str = Query(...)) -> Response:
    st = _local()
    if not st.verify("GET", key, exp, sig):
        raise PermissionDenied("Invalid or expired URL", code="invalid_signature")
    try:
        data = st.get(key)
    except FileNotFoundError as e:
        raise NotFound() from e
    ctype = (
        "image/webp"
        if key.endswith(".webp")
        else "image/jpeg"
        if key.endswith(".jpg")
        else "application/octet-stream"
    )
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "private, max-age=300"})
