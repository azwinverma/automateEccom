from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant
from app.core.context import TenantContext
from app.domains.exceptions.service import open_exceptions

router = APIRouter(tags=["exceptions"])


@router.get("/exceptions")
def list_exceptions(
    ctx: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)
) -> dict[str, Any]:
    items = open_exceptions(db, ctx.merchant_id)
    return {"items": items, "counts": dict(Counter(i["severity"] for i in items)), "total": len(items)}
