"""Plan catalog management (BIL-001..003, BIL-010).

``seed_from_file`` is idempotent: unchanged plans are left alone; a changed plan definition creates a
new PlanVersion (the previous active version is retired, existing subscriptions keep pointing at the
version they bought — grandfathering). Pricing/limits therefore change without a deploy by editing
data (admin plan editor, ADM-008, will write through the same function).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import CONTRACTS_DIR
from app.core.context import Actor, RequestMeta
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound
from app.domains.audit import service as audit
from app.domains.billing.models import (
    AddOn,
    Feature,
    MeteredResource,
    Plan,
    PlanEntitlement,
    PlanLimit,
    PlanVersion,
    Subscription,
)
from app.domains.billing.service import _add_months
from app.domains.platform import outbox

DEFAULT_PATH = CONTRACTS_DIR / "feature-entitlements.example.json"


def _hash(version_doc: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(version_doc, sort_keys=True).encode()).hexdigest()


def seed_from_file(db: Session, path: Path = DEFAULT_PATH) -> dict[str, int]:
    doc = json.loads(path.read_text())
    stats = {"features": 0, "resources": 0, "plans": 0, "versions": 0}
    for f in doc["features"]:
        row = db.get(Feature, f["code"])
        if row is None:
            db.add(Feature(code=f["code"], name=f["name"], description=f.get("description", "")))
            stats["features"] += 1
        else:
            row.name = f["name"]
    for r in doc["resources"]:
        res_row = db.get(MeteredResource, r["code"])
        if res_row is None:
            db.add(
                MeteredResource(
                    code=r["code"],
                    name=r["name"],
                    unit=r["unit"],
                    kind=r["kind"],
                    credits_per_unit=r.get("credits_per_unit", 0),
                )
            )
            stats["resources"] += 1
        else:
            res_row.name, res_row.unit, res_row.kind = r["name"], r["unit"], r["kind"]
            res_row.credits_per_unit = r.get("credits_per_unit", 0)
    db.flush()

    for p in doc["plans"]:
        plan = db.scalar(select(Plan).where(Plan.code == p["code"]))
        if plan is None:
            plan = Plan(
                code=p["code"],
                name=p["name"],
                tagline_key=p["tagline_key"],
                sort_order=p["sort_order"],
                is_public=p["is_public"],
                is_default_for_signup=p["is_default_for_signup"],
            )
            db.add(plan)
            db.flush()
            stats["plans"] += 1
        else:
            plan.name, plan.tagline_key, plan.sort_order = p["name"], p["tagline_key"], p["sort_order"]
            plan.is_public, plan.is_default_for_signup = p["is_public"], p["is_default_for_signup"]
        content_hash = _hash(p["version"])
        active = db.scalar(
            select(PlanVersion).where(PlanVersion.plan_id == plan.id, PlanVersion.status == "active")
        )
        if active is not None and active.content_hash == content_hash:
            continue
        next_no = (
            db.scalar(select(func.max(PlanVersion.version)).where(PlanVersion.plan_id == plan.id)) or 0
        ) + 1
        if active is not None:
            active.status = "retired"
            db.flush()
        v = p["version"]
        pv = PlanVersion(
            plan_id=plan.id,
            version=next_no,
            status="active",
            currency=v["currency"],
            price_monthly_minor=v["price_monthly_minor"],
            price_annual_minor=v["price_annual_minor"],
            trial_days=v["trial_days"],
            content_hash=content_hash,
        )
        db.add(pv)
        db.flush()
        for code, enabled in v["features"].items():
            db.add(PlanEntitlement(plan_version_id=pv.id, feature_code=code, enabled=enabled))
        for lim in v["limits"]:
            db.add(
                PlanLimit(
                    plan_version_id=pv.id,
                    resource_code=lim["resource"],
                    period=lim["period"],
                    limit_value=lim["limit"],
                    overage_policy=lim["overage_policy"],
                )
            )
        stats["versions"] += 1

    for a in doc.get("addons", []):
        if db.scalar(select(AddOn).where(AddOn.code == a["code"])) is None:
            db.add(
                AddOn(
                    code=a["code"],
                    name=a["name"],
                    resource_code=a.get("resource"),
                    feature_code=a.get("feature"),
                    quantity=a["quantity"],
                    price_minor=a.get("price_minor"),
                )
            )
    db.flush()
    return stats


def start_subscription(
    db: Session,
    merchant_id: uuid.UUID,
    actor: Actor,
    meta: RequestMeta | None = None,
    plan_code: str | None = None,
) -> Subscription:
    if plan_code:
        plan = db.scalar(select(Plan).where(Plan.code == plan_code))
    else:
        plan = db.scalar(select(Plan).where(Plan.is_default_for_signup.is_(True)).order_by(Plan.sort_order))
    if plan is None:
        raise NotFound(
            "No signup plan configured; run `python -m app.cli seed-plans`", code="plan_not_configured"
        )
    pv = db.scalar(select(PlanVersion).where(PlanVersion.plan_id == plan.id, PlanVersion.status == "active"))
    if pv is None:
        raise Conflict("Plan has no active version", code="plan_not_configured")
    now = utcnow()
    trialing = pv.trial_days > 0
    sub = Subscription(
        merchant_id=merchant_id,
        plan_version_id=pv.id,
        status="trialing" if trialing else "active",
        billing_interval="month",
        trial_ends_at=now + timedelta(days=pv.trial_days) if trialing else None,
        current_period_start=now,
        current_period_end=_add_months(now, 1),
    )
    db.add(sub)
    db.flush()
    audit.record(
        db,
        action="billing.subscription_started",
        resource_type="subscription",
        resource_id=sub.id,
        actor=actor,
        merchant_id=merchant_id,
        meta=meta,
        metadata={"plan": plan.code, "plan_version": pv.version, "status": sub.status},
    )
    outbox.publish(
        db,
        event_type="billing.subscription_started",
        aggregate_type="subscription",
        aggregate_id=sub.id,
        merchant_id=merchant_id,
        payload={"subscription_id": str(sub.id), "plan_code": plan.code, "status": sub.status},
    )
    return sub
