from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.context import TenantContext
from app.domains.ai import credentials
from app.domains.ai.models import ProviderCredential

router = APIRouter(prefix="/ai", tags=["ai"])


class CredentialOut(BaseModel):
    id: uuid.UUID
    provider: str
    key_last4: str
    status: str
    fallback_to_platform: bool
    last_tested_at: datetime | None
    last_test_ok: bool | None
    rotated_at: datetime | None
    created_at: datetime

    @staticmethod
    def of(c: ProviderCredential) -> CredentialOut:
        return CredentialOut(
            id=c.id,
            provider=c.provider,
            key_last4=c.key_last4,
            status=c.status,
            fallback_to_platform=c.fallback_to_platform,
            last_tested_at=c.last_tested_at,
            last_test_ok=c.last_test_ok,
            rotated_at=c.rotated_at,
            created_at=c.created_at,
        )


class CredentialIn(BaseModel):
    provider: Literal["anthropic", "openai", "gemini"]
    api_key: SecretStr = Field(min_length=20, max_length=400)
    fallback_to_platform: bool = True


class RotateIn(BaseModel):
    api_key: SecretStr = Field(min_length=20, max_length=400)
    fallback_to_platform: bool | None = None


@router.get("/credentials")
def list_credentials(
    ctx: TenantContext = Depends(require("ai.credentials.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    rows = db.scalars(
        select(ProviderCredential).where(
            ProviderCredential.merchant_id == ctx.merchant_id, ProviderCredential.status == "active"
        )
    )
    return {"items": [CredentialOut.of(c) for c in rows]}


@router.post("/credentials", status_code=201, response_model=CredentialOut)
def create_credential(
    body: CredentialIn,
    ctx: TenantContext = Depends(require("ai.credentials.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> CredentialOut:
    return CredentialOut.of(
        credentials.create(db, ctx, body.provider, body.api_key.get_secret_value(), body.fallback_to_platform)
    )


@router.post("/credentials/{cred_id}/rotate", response_model=CredentialOut)
def rotate_credential(
    cred_id: uuid.UUID,
    body: RotateIn,
    ctx: TenantContext = Depends(require("ai.credentials.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> CredentialOut:
    return CredentialOut.of(
        credentials.rotate(db, ctx, cred_id, body.api_key.get_secret_value(), body.fallback_to_platform)
    )


@router.post("/credentials/{cred_id}/test")
def test_credential(
    cred_id: uuid.UUID,
    ctx: TenantContext = Depends(require("ai.credentials.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict:
    return {"ok": credentials.test(db, ctx, cred_id)}


@router.delete("/credentials/{cred_id}", status_code=204)
def revoke_credential(
    cred_id: uuid.UUID,
    ctx: TenantContext = Depends(require("ai.credentials.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    credentials.revoke(db, ctx, cred_id)
    return Response(status_code=204)
