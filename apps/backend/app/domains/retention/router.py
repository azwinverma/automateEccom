"""Retain: retention campaigns API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.domains.retention import service
from app.domains.retention.models import Campaign

router = APIRouter(prefix="/retention", tags=["retention"])


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(pattern="^(win_back|repeat_reminder|broadcast)$")
    days: int | None = Field(default=None, ge=1, le=365)
    segment: str | None = Field(default=None, pattern="^(all|repeat|new|inactive)$")
    message_en: str | None = Field(default=None, max_length=1000)
    message_ne: str | None = Field(default=None, max_length=1000)
    daily_limit: int = Field(default=200, ge=1, le=2000)


class CampaignPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    days: int | None = Field(default=None, ge=1, le=365)
    segment: str | None = Field(default=None, pattern="^(all|repeat|new|inactive)$")
    message_en: str | None = Field(default=None, max_length=1000)
    message_ne: str | None = Field(default=None, max_length=1000)
    daily_limit: int | None = Field(default=None, ge=1, le=2000)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|paused|completed)$")


@router.get("/templates")
def templates(ctx: TenantContext = Depends(require("customers.read"))) -> dict[str, Any]:
    return {
        "items": [
            {
                "kind": k,
                "message_en": v["en"],
                "message_ne": v["ne"],
                "default_days": service.DEFAULT_DAYS.get(k),
            }
            for k, v in service.TEMPLATES.items()
        ],
        "placeholders": list(service.PLACEHOLDERS),
    }


@router.get("/campaigns")
def list_campaigns(
    ctx: TenantContext = Depends(require("customers.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    rows = db.scalars(select(Campaign).order_by(Campaign.created_at.desc()))
    return {"items": [service.view(db, c) for c in rows]}


@router.post("/campaigns", status_code=201)
def create_campaign(
    body: CampaignIn,
    ctx: TenantContext = Depends(require("automation.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.view(db, service.create(db, ctx, **body.model_dump()))


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: uuid.UUID,
    ctx: TenantContext = Depends(require("customers.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.view(db, service.get(db, ctx, campaign_id))


@router.patch("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignPatch,
    ctx: TenantContext = Depends(require("automation.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return service.view(db, service.update(db, ctx, campaign_id, **body.model_dump()))


@router.post("/campaigns/{campaign_id}/preview")
def preview_campaign(
    campaign_id: uuid.UUID,
    ctx: TenantContext = Depends(require("customers.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Who it would reach now and who it can't (and why). Sends nothing."""
    return service.preview(db, ctx, campaign_id)


@router.post("/campaigns/{campaign_id}/status")
def set_campaign_status(
    campaign_id: uuid.UUID,
    body: StatusIn,
    ctx: TenantContext = Depends(require("automation.approve")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Starting a campaign is the seller's approval for it to message customers."""
    return service.view(db, service.set_status(db, ctx, campaign_id, body.status))
