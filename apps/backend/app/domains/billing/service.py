"""Entitlement service (BIL-004, BIL-008, BIL-009).

Pipeline for every paid/expensive capability:
    require_feature → reserve (check limits under row locks) → execute → finalize | release

Rules:
* Business code passes feature codes / resource codes. It never sees plan names.
* A resource with no limit row in the effective plan is NOT included (deny by default). Unlimited
  must be explicit (limit_value = NULL).
* Consumable resources (AI generations, orders) are counted per window (billing month, merchant-
  local day). Gauge resources (products, members) are checked against a caller-supplied current count.
* Daily burst limits are always hard limits. Monthly limits follow the limit's overage policy:
  ``block``, ``credits`` (spend wallet credits; funded usage does not consume monthly quota) or
  ``overage`` (allowed, billed later).
* Reserve must be called in a short transaction and committed BEFORE the slow provider call; the
  AI gateway does this. Expired reservations are released by a periodic task.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import FeatureNotInPlan, NotFound, UsageLimitReached
from app.core.ids import uuid7
from app.core.metrics import USAGE_BLOCKS
from app.domains.billing.models import (
    AddOn,
    CreditTransaction,
    CreditWallet,
    EntitlementOverride,
    MeteredResource,
    Plan,
    PlanEntitlement,
    PlanLimit,
    PlanVersion,
    Subscription,
    SubscriptionAddOn,
    UsageAlert,
    UsageCounter,
    UsageEvent,
    UsageReservation,
)
from app.domains.merchants.models import Merchant
from app.domains.platform import outbox

log = structlog.get_logger(__name__)

LIVE_STATUSES = ("trialing", "active", "past_due")
ALERT_THRESHOLDS = (70, 85, 100)
EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
DEFAULT_RESERVATION_TTL = timedelta(minutes=30)


@dataclass(frozen=True)
class LimitRule:
    resource: str
    period: str
    limit: int | None  # None = unlimited
    overage_policy: str


@dataclass
class Entitlements:
    merchant_id: uuid.UUID
    subscription: Subscription | None
    plan_code: str | None
    features: dict[str, bool] = field(default_factory=dict)
    limits: dict[tuple[str, str], LimitRule] = field(default_factory=dict)

    def has(self, feature: str) -> bool:
        return self.features.get(feature, False)

    def rules_for(self, resource: str) -> list[LimitRule]:
        return [r for (res, _), r in self.limits.items() if res == resource]


def _add_months(dt: datetime, months: int) -> datetime:
    y, m = divmod(dt.month - 1 + months, 12)
    year, month = dt.year + y, m + 1
    days_in_month = [
        31,
        29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ][month - 1]
    return dt.replace(year=year, month=month, day=min(dt.day, days_in_month))


def window(period: str, now: datetime, sub: Subscription | None, tz: str) -> tuple[datetime, datetime | None]:
    """Return [start, end) of the usage window containing ``now``."""
    if period == "lifetime":
        return EPOCH, None
    if period == "day":
        local = now.astimezone(ZoneInfo(tz))
        start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start_local.astimezone(UTC)
        return start, (start_local + timedelta(days=1)).astimezone(UTC)
    if period == "month":
        anchor = (
            sub.current_period_start if sub else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        start = anchor
        while _add_months(start, 1) <= now:  # roll forward if renewal job hasn't run yet
            start = _add_months(start, 1)
        while start > now:
            start = _add_months(start, -1)
        return start, _add_months(start, 1)
    raise ValueError(f"unknown period {period}")


GaugeCounter = Callable[[Session, uuid.UUID], int]
GAUGE_COUNTERS: dict[str, GaugeCounter] = {}


def register_gauge(resource: str) -> Callable[[GaugeCounter], GaugeCounter]:
    """Domains register how to count their gauge resources (current products, seats...).

    Counters must filter by ``merchant_id`` explicitly: they also run in admin (non-tenant) sessions.
    """

    def deco(fn: GaugeCounter) -> GaugeCounter:
        GAUGE_COUNTERS[resource] = fn
        return fn

    return deco


class EntitlementService:
    # ------------------------------------------------------------------ resolution
    def resolve(self, db: Session, merchant_id: uuid.UUID) -> Entitlements:
        sub = db.scalar(
            select(Subscription)
            .where(Subscription.merchant_id == merchant_id, Subscription.status.in_(LIVE_STATUSES))
            .execution_options(skip_tenant_filter=True)
        )
        ent = Entitlements(merchant_id=merchant_id, subscription=sub, plan_code=None)
        if sub is None:
            return ent
        pv = db.get(PlanVersion, sub.plan_version_id)
        plan = db.get(Plan, pv.plan_id) if pv else None
        ent.plan_code = plan.code if plan else None
        for pe in db.scalars(
            select(PlanEntitlement).where(PlanEntitlement.plan_version_id == sub.plan_version_id)
        ):
            ent.features[pe.feature_code] = pe.enabled
        for pl in db.scalars(select(PlanLimit).where(PlanLimit.plan_version_id == sub.plan_version_id)):
            ent.limits[(pl.resource_code, pl.period)] = LimitRule(
                pl.resource_code, pl.period, pl.limit_value, pl.overage_policy
            )
        # Add-ons extend limits / enable features.
        rows = db.execute(
            select(AddOn, SubscriptionAddOn.quantity)
            .join(SubscriptionAddOn, SubscriptionAddOn.addon_id == AddOn.id)
            .where(SubscriptionAddOn.subscription_id == sub.id, SubscriptionAddOn.active.is_(True))
            .execution_options(skip_tenant_filter=True)
        ).all()
        for addon, qty in rows:
            if addon.feature_code:
                ent.features[addon.feature_code] = True
            if addon.resource_code and addon.period:
                key = (addon.resource_code, addon.period)
                cur = ent.limits.get(key)
                if cur is not None and cur.limit is not None:
                    ent.limits[key] = LimitRule(
                        cur.resource, cur.period, cur.limit + addon.quantity * qty, cur.overage_policy
                    )
        # Admin overrides win.
        now = utcnow()
        for o in db.scalars(
            select(EntitlementOverride)
            .where(
                EntitlementOverride.merchant_id == merchant_id,
                or_(EntitlementOverride.expires_at.is_(None), EntitlementOverride.expires_at > now),
            )
            .execution_options(skip_tenant_filter=True)
        ):
            if o.feature_code is not None and o.enabled is not None:
                ent.features[o.feature_code] = o.enabled
            elif o.resource_code is not None and o.period is not None:
                cur = ent.limits.get((o.resource_code, o.period))
                ent.limits[(o.resource_code, o.period)] = LimitRule(
                    o.resource_code, o.period, o.limit_value, cur.overage_policy if cur else "block"
                )
        return ent

    def require_feature(self, db: Session, merchant_id: uuid.UUID, feature: str) -> Entitlements:
        ent = self.resolve(db, merchant_id)
        if not ent.has(feature):
            raise FeatureNotInPlan(
                details={
                    "feature": feature,
                    "plan": ent.plan_code,
                    "upgrade_options": self._plans_with(db, feature),
                }
            )
        return ent

    def _plans_with(self, db: Session, feature: str) -> list[str]:
        rows = db.execute(
            select(Plan.code)
            .join(PlanVersion, PlanVersion.plan_id == Plan.id)
            .join(PlanEntitlement, PlanEntitlement.plan_version_id == PlanVersion.id)
            .where(
                PlanVersion.status == "active",
                PlanEntitlement.feature_code == feature,
                PlanEntitlement.enabled.is_(True),
                Plan.is_public.is_(True),
            )
            .order_by(Plan.sort_order)
        ).all()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------ gauges
    def check_gauge(
        self, db: Session, merchant_id: uuid.UUID, resource: str, current: int | None = None, adding: int = 1
    ) -> None:
        """Block if adding ``adding`` units would exceed the gauge limit. ``current`` defaults to the
        registered counter so the enforced number and the displayed number are the same query."""
        if current is None:
            counter = GAUGE_COUNTERS.get(resource)
            if counter is None:
                raise LookupError(f"no gauge counter registered for {resource}")
            current = counter(db, merchant_id)
        ent = self.resolve(db, merchant_id)
        rule = ent.limits.get((resource, "lifetime"))
        if rule is None:
            self._block(resource, "lifetime", 0, current, None, ent)
        assert rule is not None
        if rule.limit is not None and current + adding > rule.limit:
            self._block(resource, "lifetime", rule.limit, current, None, ent)

    # ------------------------------------------------------------------ consumables
    def _merchant_tz(self, db: Session, merchant_id: uuid.UUID) -> str:
        m = db.get(Merchant, merchant_id)
        if m is None:
            raise NotFound()
        return m.timezone

    def _counter(
        self,
        db: Session,
        merchant_id: uuid.UUID,
        resource: str,
        period: str,
        start: datetime,
        end: datetime | None,
    ) -> UsageCounter:
        db.flush()  # populate_existing below must not clobber pending in-memory changes
        db.execute(
            pg_insert(UsageCounter)
            .values(
                id=uuid7(),
                merchant_id=merchant_id,
                resource_code=resource,
                period=period,
                period_start=start,
                period_end=end,
                used=0,
                reserved=0,
                updated_at=utcnow(),
            )
            .on_conflict_do_nothing(index_elements=["merchant_id", "resource_code", "period", "period_start"])
        )
        counter = db.scalar(
            select(UsageCounter)
            .where(
                UsageCounter.merchant_id == merchant_id,
                UsageCounter.resource_code == resource,
                UsageCounter.period == period,
                UsageCounter.period_start == start,
            )
            .with_for_update()
            .execution_options(skip_tenant_filter=True, populate_existing=True)
        )
        assert counter is not None
        return counter

    def _block(
        self,
        resource: str,
        period: str,
        limit: int,
        used: int,
        period_end: datetime | None,
        ent: Entitlements,
        credits_needed: int | None = None,
    ) -> None:
        USAGE_BLOCKS.labels(resource).inc()
        options = ["upgrade"]
        if period == "month" or credits_needed:
            options.insert(0, "buy_credits")
        if period in ("month", "day"):
            options.append("wait_for_renewal")
        raise UsageLimitReached(
            details={
                "resource": resource,
                "period": period,
                "limit": limit,
                "used": used,
                "period_end": period_end.isoformat() if period_end else None,
                "plan": ent.plan_code,
                "credits_needed": credits_needed,
                "options": options,
            }
        )

    def reserve(
        self,
        db: Session,
        merchant_id: uuid.UUID,
        resource: str,
        quantity: int,
        idempotency_key: str,
        *,
        reference_type: str | None = None,
        reference_id: str | None = None,
        ttl: timedelta = DEFAULT_RESERVATION_TTL,
    ) -> UsageReservation:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        existing = db.scalar(
            select(UsageReservation)
            .where(
                UsageReservation.merchant_id == merchant_id,
                UsageReservation.idempotency_key == idempotency_key,
            )
            .execution_options(skip_tenant_filter=True)
        )
        if existing is not None:
            return existing

        ent = self.resolve(db, merchant_id)
        rules = sorted(ent.rules_for(resource), key=lambda r: r.period)  # stable lock order: day < month
        if not rules:
            self._block(resource, "month", 0, 0, None, ent)
        res_def = db.get(MeteredResource, resource)
        tz = self._merchant_tz(db, merchant_id)
        now = utcnow()

        counters: dict[str, UsageCounter] = {}
        for rule in rules:
            start, end = window(rule.period, now, ent.subscription, tz)
            counters[rule.period] = self._counter(db, merchant_id, resource, rule.period, start, end)

        funding = "quota"
        credits_held = 0
        for rule in rules:
            c = counters[rule.period]
            if rule.limit is None or c.used + c.reserved + quantity <= rule.limit:
                continue
            if rule.period == "month" and rule.overage_policy == "overage":
                funding = "overage"
                continue
            if (
                rule.period == "month"
                and rule.overage_policy == "credits"
                and res_def
                and res_def.credits_per_unit
            ):
                need = quantity * res_def.credits_per_unit
                wallet = self._wallet(db, merchant_id, lock=True)
                if wallet.balance >= need:
                    funding = "credits"
                    credits_held = need
                    continue
                self._block(resource, rule.period, rule.limit, c.used, c.period_end, ent, credits_needed=need)
            self._block(resource, rule.period, rule.limit, c.used, c.period_end, ent)

        touched = [c for p, c in counters.items() if not (funding == "credits" and p == "month")]
        for c in touched:
            c.reserved += quantity
        reservation = UsageReservation(
            merchant_id=merchant_id,
            resource_code=resource,
            quantity=quantity,
            funding=funding,
            credits_held=credits_held,
            idempotency_key=idempotency_key,
            counter_ids=",".join(str(c.id) for c in touched),
            reference_type=reference_type,
            reference_id=reference_id,
            expires_at=now + ttl,
        )
        db.add(reservation)
        db.flush()
        if credits_held:
            self._credit_tx(
                db,
                merchant_id,
                -credits_held,
                "hold",
                f"hold:{reservation.id}",
                "usage_reservation",
                str(reservation.id),
            )
        return reservation

    def _locked_reservation(self, db: Session, reservation_id: uuid.UUID) -> UsageReservation:
        r = db.scalar(
            select(UsageReservation)
            .where(UsageReservation.id == reservation_id)
            .with_for_update()
            .execution_options(skip_tenant_filter=True, populate_existing=True)
        )
        if r is None:
            raise NotFound()
        return r

    def _touched_counters(self, db: Session, r: UsageReservation) -> list[UsageCounter]:
        ids = [uuid.UUID(x) for x in r.counter_ids.split(",") if x]
        return list(
            db.scalars(
                select(UsageCounter)
                .where(UsageCounter.id.in_(ids))
                .order_by(UsageCounter.period)
                .with_for_update()
                .execution_options(skip_tenant_filter=True, populate_existing=True)
            )
        )

    def finalize(
        self, db: Session, reservation_id: uuid.UUID, actual_quantity: int | None = None
    ) -> UsageEvent | None:
        r = self._locked_reservation(db, reservation_id)
        if r.status == "finalized":
            return db.scalar(
                select(UsageEvent)
                .where(UsageEvent.reservation_id == r.id)
                .execution_options(skip_tenant_filter=True)
            )
        if r.status != "reserved":
            log.warning("finalize_on_settled_reservation", reservation_id=str(r.id), status=r.status)
            return None
        actual = r.quantity if actual_quantity is None else max(0, min(actual_quantity, r.quantity))
        for c in self._touched_counters(db, r):
            c.reserved = max(0, c.reserved - r.quantity)
            c.used += actual
        credits_charged = 0
        if r.credits_held:
            per_unit = r.credits_held // r.quantity
            credits_charged = per_unit * actual
            refund = r.credits_held - credits_charged
            if refund:
                self._credit_tx(
                    db, r.merchant_id, refund, "release", f"release:{r.id}", "usage_reservation", str(r.id)
                )
        r.status = "finalized"
        r.finalized_quantity = actual
        r.settled_at = utcnow()
        event = UsageEvent(
            merchant_id=r.merchant_id,
            resource_code=r.resource_code,
            quantity=actual,
            funding=r.funding,
            credits_charged=credits_charged,
            reservation_id=r.id,
            idempotency_key=f"res:{r.id}",
            reference_type=r.reference_type,
            reference_id=r.reference_id,
        )
        db.add(event)
        db.flush()
        self._check_alerts(db, r.merchant_id, r.resource_code)
        return event

    def release(self, db: Session, reservation_id: uuid.UUID, status: str = "released") -> None:
        r = self._locked_reservation(db, reservation_id)
        if r.status != "reserved":
            return
        for c in self._touched_counters(db, r):
            c.reserved = max(0, c.reserved - r.quantity)
        if r.credits_held:
            self._credit_tx(
                db,
                r.merchant_id,
                r.credits_held,
                "release",
                f"release:{r.id}",
                "usage_reservation",
                str(r.id),
            )
        r.status = status
        r.settled_at = utcnow()

    def record(
        self,
        db: Session,
        merchant_id: uuid.UUID,
        resource: str,
        quantity: int,
        idempotency_key: str,
        **ref: str | None,
    ) -> UsageEvent | None:
        """Reserve + finalize in one step (for usage that happens inside the current transaction)."""
        r = self.reserve(db, merchant_id, resource, quantity, idempotency_key, **ref)  # type: ignore[arg-type]
        return self.finalize(db, r.id)

    def release_expired(self, db: Session, limit: int = 500) -> int:
        ids = list(
            db.scalars(
                select(UsageReservation.id)
                .where(UsageReservation.status == "reserved", UsageReservation.expires_at < utcnow())
                .limit(limit)
                .execution_options(skip_tenant_filter=True)
            )
        )
        for rid in ids:
            self.release(db, rid, status="expired")
        return len(ids)

    # ------------------------------------------------------------------ alerts
    def _check_alerts(self, db: Session, merchant_id: uuid.UUID, resource: str) -> None:
        ent = self.resolve(db, merchant_id)
        rule = ent.limits.get((resource, "month"))
        if rule is None or not rule.limit:
            return
        tz = self._merchant_tz(db, merchant_id)
        start, _ = window("month", utcnow(), ent.subscription, tz)
        c = db.scalar(
            select(UsageCounter)
            .where(
                UsageCounter.merchant_id == merchant_id,
                UsageCounter.resource_code == resource,
                UsageCounter.period == "month",
                UsageCounter.period_start == start,
            )
            .execution_options(skip_tenant_filter=True)
        )
        if c is None:
            return
        pct = c.used * 100 / rule.limit
        for t in ALERT_THRESHOLDS:
            if pct < t:
                break
            inserted = db.execute(
                pg_insert(UsageAlert)
                .values(
                    id=uuid7(),
                    merchant_id=merchant_id,
                    resource_code=resource,
                    period="month",
                    period_start=start,
                    threshold=t,
                    created_at=utcnow(),
                )
                .on_conflict_do_nothing()
                .returning(UsageAlert.id)
            ).scalar_one_or_none()
            if inserted:
                outbox.publish(
                    db,
                    event_type="billing.usage_threshold_reached",
                    aggregate_type="merchant",
                    aggregate_id=merchant_id,
                    merchant_id=merchant_id,
                    payload={
                        "resource": resource,
                        "period": "month",
                        "threshold": t,
                        "used": int(c.used),
                        "limit": int(rule.limit),
                    },
                )

    # ------------------------------------------------------------------ credits
    def _wallet(self, db: Session, merchant_id: uuid.UUID, lock: bool = False) -> CreditWallet:
        db.flush()  # populate_existing below must not clobber pending in-memory changes
        db.execute(
            pg_insert(CreditWallet)
            .values(id=uuid7(), merchant_id=merchant_id, balance=0, created_at=utcnow(), updated_at=utcnow())
            .on_conflict_do_nothing(index_elements=["merchant_id"])
        )
        stmt = (
            select(CreditWallet)
            .where(CreditWallet.merchant_id == merchant_id)
            .execution_options(skip_tenant_filter=True, populate_existing=True)
        )
        if lock:
            stmt = stmt.with_for_update()
        w = db.scalar(stmt)
        assert w is not None
        return w

    def _credit_tx(
        self,
        db: Session,
        merchant_id: uuid.UUID,
        amount: int,
        kind: str,
        key: str,
        ref_type: str | None = None,
        ref_id: str | None = None,
        note: str | None = None,
    ) -> CreditTransaction:
        existing = db.scalar(
            select(CreditTransaction)
            .where(CreditTransaction.merchant_id == merchant_id, CreditTransaction.idempotency_key == key)
            .execution_options(skip_tenant_filter=True)
        )
        if existing:
            return existing
        w = self._wallet(db, merchant_id, lock=True)
        if w.balance + amount < 0:
            raise UsageLimitReached(
                "Insufficient credits",
                code="insufficient_credits",
                details={"balance": w.balance, "required": -amount, "options": ["buy_credits"]},
            )
        w.balance += amount
        tx = CreditTransaction(
            merchant_id=merchant_id,
            wallet_id=w.id,
            amount=amount,
            balance_after=w.balance,
            kind=kind,
            idempotency_key=key,
            reference_type=ref_type,
            reference_id=ref_id,
            note=note,
        )
        db.add(tx)
        db.flush()
        return tx

    def grant_credits(
        self,
        db: Session,
        merchant_id: uuid.UUID,
        amount: int,
        key: str,
        kind: str = "grant",
        note: str | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("amount must be positive")
        return self._credit_tx(db, merchant_id, amount, kind, key, note=note)

    def balance(self, db: Session, merchant_id: uuid.UUID) -> int:
        return self._wallet(db, merchant_id).balance

    # ------------------------------------------------------------------ reporting
    def usage_summary(self, db: Session, merchant_id: uuid.UUID) -> list[dict[str, object]]:
        ent = self.resolve(db, merchant_id)
        tz = self._merchant_tz(db, merchant_id)
        now = utcnow()
        resources = {r.code: r for r in db.scalars(select(MeteredResource))}
        out: dict[str, dict[str, object]] = {}
        for (res, period), rule in sorted(ent.limits.items()):
            res_def = resources.get(res)
            entry = out.setdefault(
                res,
                {
                    "resource": res,
                    "unit": res_def.unit if res_def else None,
                    "kind": res_def.kind if res_def else None,
                },
            )
            if res_def and res_def.kind == "gauge":
                counter = GAUGE_COUNTERS.get(res)
                used_now = counter(db, merchant_id) if counter else None  # None = not counted yet
                entry.update(
                    {
                        "period": "lifetime",
                        "limit": rule.limit,
                        "used": used_now,
                        "reserved": 0,
                        "included": rule.limit != 0,
                        "alert_level": _alert_level(used_now, rule.limit) if used_now is not None else None,
                        "overage_policy": rule.overage_policy,
                    }
                )
                continue
            start, end = window(period, now, ent.subscription, tz)
            c = db.scalar(
                select(UsageCounter)
                .where(
                    and_(
                        UsageCounter.merchant_id == merchant_id,
                        UsageCounter.resource_code == res,
                        UsageCounter.period == period,
                        UsageCounter.period_start == start,
                    )
                )
                .execution_options(skip_tenant_filter=True)
            )
            used, reserved = (c.used, c.reserved) if c else (0, 0)
            block = {
                "period": period,
                "limit": rule.limit,
                "used": used,
                "reserved": reserved,
                "period_end": end.isoformat() if end else None,
                "overage_policy": rule.overage_policy,
                "alert_level": _alert_level(used, rule.limit),
                "included": rule.limit != 0,
            }
            if period == "day":
                entry["burst"] = block
            else:
                entry.update(block)
        return list(out.values())


def _alert_level(used: int, limit: int | None) -> str | None:
    if not limit:
        return "100" if limit == 0 else None
    pct = used * 100 / limit
    level = None
    for t in ALERT_THRESHOLDS:
        if pct >= t:
            level = str(t)
    return level


entitlements = EntitlementService()
