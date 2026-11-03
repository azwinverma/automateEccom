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
    ctx: TenantContext = Depends(get_tenant), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    # Plan limits are only shown to people who can see billing (and so can act on them).
    items = open_exceptions(db, ctx.merchant_id, include_usage=ctx.has("billing.read"))
    return {"items": items, "counts": dict(Counter(i["severity"] for i in items)), "total": len(items)}
