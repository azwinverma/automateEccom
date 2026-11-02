from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.core.errors import ValidationFailed
from app.domains.content import service
from app.domains.content.models import ContentPost

router = APIRouter(prefix="/content", tags=["content"])
Kind = Literal["post", "story", "reel"]


class PostIn(BaseModel):
    connection_id: uuid.UUID
    caption: str = Field(min_length=1, max_length=5000)
    hashtags: list[str] = Field(default_factory=list, max_length=30)
    asset_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    kind: Kind = "post"
    product_id: uuid.UUID | None = None
    campaign: str | None = Field(default=None, max_length=80)


class PostPatch(BaseModel):
    version: int | None = None
    caption: str | None = Field(default=None, min_length=1, max_length=5000)
    hashtags: list[str] | None = Field(default=None, max_length=30)


class FromStudioIn(BaseModel):
    job_id: uuid.UUID
    connection_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    kind: Kind = "post"


class ScheduleIn(BaseModel):
    at: datetime | None = Field(default=None, description="UTC; omit to publish now")


class RejectIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


@router.get("/posts")
def calendar(
    start: datetime | None = Query(None, alias="from"),
    end: datetime | None = Query(None, alias="to"),
    status: str | None = None,
    ctx: TenantContext = Depends(require("content.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if start and end and (end - start).days > 93:
        raise ValidationFailed("Calendar range can be at most 3 months", code="range_too_large")
    stmt = select(ContentPost).order_by(
        ContentPost.scheduled_at.asc().nulls_last(), ContentPost.created_at.desc()
    )
    if start:
        stmt = stmt.where(ContentPost.scheduled_at >= start)
    if end:
        stmt = stmt.where(ContentPost.scheduled_at < end)
    if status:
        stmt = stmt.where(ContentPost.status == status)
    return {"items": [service.post_view(p) for p in db.scalars(stmt.limit(500))]}


@router.post("/posts", status_code=201)
def create(
    body: PostIn, ctx: TenantContext = Depends(require("content.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.post_view(service.create_post(db, ctx, **body.model_dump()))


@router.post("/posts/from-studio", status_code=201)
def from_studio(
    body: FromStudioIn, ctx: TenantContext = Depends(require("content.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return {
        "items": [
            service.post_view(p)
            for p in service.from_studio(db, ctx, body.job_id, body.connection_ids, body.kind)
        ]
    }


@router.patch("/posts/{post_id}")
def update(
    post_id: uuid.UUID,
    body: PostPatch,
    ctx: TenantContext = Depends(require("content.write")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return service.post_view(
        service.update_post(
            db, ctx, post_id, body.version, body.model_dump(exclude_unset=True, exclude={"version"})
        )
    )


@router.post("/posts/{post_id}/submit")
def submit(
    post_id: uuid.UUID, ctx: TenantContext = Depends(require("content.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.post_view(service.submit(db, ctx, post_id))


@router.post("/posts/{post_id}/approve")
def approve(
    post_id: uuid.UUID, ctx: TenantContext = Depends(require("content.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.post_view(service.approve(db, ctx, post_id))


@router.post("/posts/{post_id}/reject")
def reject(
    post_id: uuid.UUID,
    body: RejectIn,
    ctx: TenantContext = Depends(require("content.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return service.post_view(service.reject(db, ctx, post_id, body.note))


@router.post("/posts/{post_id}/schedule")
def schedule(
    post_id: uuid.UUID,
    body: ScheduleIn,
    ctx: TenantContext = Depends(require("content.publish")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return service.post_view(service.schedule(db, ctx, post_id, body.at))


@router.post("/posts/{post_id}/unschedule")
def unschedule(
    post_id: uuid.UUID,
    ctx: TenantContext = Depends(require("content.publish")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return service.post_view(service.unschedule(db, ctx, post_id))


@router.post("/posts/{post_id}/cancel")
def cancel(
    post_id: uuid.UUID, ctx: TenantContext = Depends(require("content.write")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return service.post_view(service.cancel(db, ctx, post_id))
