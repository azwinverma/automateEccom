from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.api.idempotent import run_idempotent
from app.core.context import TenantContext
from app.domains.catalog import service as catalog
from app.domains.catalog.router import ProductIn
from app.domains.studio import service
from app.domains.studio.models import StudioJob

router = APIRouter(prefix="/studio", tags=["studio"])


class JobIn(BaseModel):
    asset_ids: list[uuid.UUID] = Field(min_length=1, max_length=service.MAX_IMAGES)
    locale: Literal["en", "ne"] = "ne"
    seller_notes: str | None = Field(default=None, max_length=2000)


class ApplyIn(BaseModel):
    product: ProductIn
    accepted_attribute_keys: list[str] = Field(default_factory=list, max_length=50)
    category_path: list[str] | None = Field(default=None, max_length=6)


@router.post("/jobs", status_code=202)
def create_job(
    body: JobIn,
    ctx: TenantContext = Depends(require("ai.use")),
    db: Session = Depends(get_db),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Any:
    def _do() -> dict[str, Any]:
        return service.job_view(service.create_job(db, ctx, body.asset_ids, body.locale, body.seller_notes))

    return run_idempotent(
        db,
        key=idem,
        owner=f"merchant:{ctx.merchant_id}",
        scope="studio.jobs.create",
        body=body.model_dump(mode="json"),
        status_code=202,
        fn=_do,
    )


@router.get("/jobs/{job_id}")
def get_job(
    job_id: uuid.UUID, ctx: TenantContext = Depends(require("catalog.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.job_view(service._get(db, ctx, job_id))


@router.get("/jobs")
def list_jobs(
    status: Literal["queued", "running", "ready", "failed", "applied", "discarded"] | None = None,
    limit: int = Query(30, ge=1, le=100),
    ctx: TenantContext = Depends(require("catalog.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(StudioJob).order_by(StudioJob.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(StudioJob.status == status)
    return {"items": [service.job_view(j) for j in db.scalars(stmt)]}


@router.post("/jobs/{job_id}/apply", status_code=201)
def apply_job(
    job_id: uuid.UUID,
    body: ApplyIn,
    ctx: TenantContext = Depends(require("catalog.write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    p = body.product
    data = catalog.ProductInput(
        **p.model_dump(exclude={"options", "variants"}),
        options=[catalog.OptionInput(o.name, o.values) for o in p.options],
        variants=[catalog.VariantInput(**v.model_dump()) for v in p.variants],
    )
    pid = service.apply_job(db, ctx, job_id, data, body.accepted_attribute_keys, body.category_path)
    return catalog.product_detail(db, ctx, pid)


@router.post("/jobs/{job_id}/discard", status_code=204)
def discard_job(
    job_id: uuid.UUID, ctx: TenantContext = Depends(require("catalog.write")), db: Session = Depends(get_db)
) -> Response:
    service.discard_job(db, ctx, job_id)
    return Response(status_code=204)


@router.post("/jobs/{job_id}/retry", status_code=202)
def retry_job(
    job_id: uuid.UUID, ctx: TenantContext = Depends(require("ai.use")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.job_view(service.retry_job(db, ctx, job_id))
