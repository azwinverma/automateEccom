"""Feature flags (FND-011): release toggles, NOT plan entitlements (those live in billing).

Evaluation order: kill switch → merchant override → percentage rollout (stable hash) → default.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.platform.models import FeatureFlag, FeatureFlagOverride


def _bucket(flag_key: str, merchant_id: uuid.UUID) -> int:
    return int(hashlib.sha256(f"{flag_key}:{merchant_id}".encode()).hexdigest()[:8], 16) % 100


def evaluate(flag: FeatureFlag, override: bool | None, merchant_id: uuid.UUID | None) -> bool:
    if flag.kill_switch:
        return False
    if override is not None:
        return override
    if merchant_id is not None and flag.rollout_percentage > 0:
        return _bucket(flag.key, merchant_id) < flag.rollout_percentage
    return flag.default_enabled


def evaluate_all(db: Session, merchant_id: uuid.UUID | None) -> dict[str, bool]:
    flags = db.scalars(select(FeatureFlag)).all()
    overrides: dict[str, bool] = {}
    if merchant_id is not None:
        overrides = {
            o.flag_key: o.enabled
            for o in db.scalars(
                select(FeatureFlagOverride).where(FeatureFlagOverride.merchant_id == merchant_id)
            )
        }
    return {f.key: evaluate(f, overrides.get(f.key), merchant_id) for f in flags}


def is_enabled(db: Session, key: str, merchant_id: uuid.UUID | None) -> bool:
    flag = db.get(FeatureFlag, key)
    if flag is None:
        return False
    override = None
    if merchant_id is not None:
        o = db.scalar(
            select(FeatureFlagOverride).where(
                FeatureFlagOverride.flag_key == key, FeatureFlagOverride.merchant_id == merchant_id
            )
        )
        override = o.enabled if o else None
    return evaluate(flag, override, merchant_id)
