"""Autonomous Decision Policy (AUT-016/017/019) and the operational action log (AUT-018).

``decide()`` is the one function every automated action goes through (workflow steps, the Sales
Agent's auto-send, delivery recovery, return auto-approval). It returns a DecisionRecord:
AUTO_EXECUTE, REQUIRE_APPROVAL or BLOCK, the rule that decided, and the inputs it used.

Rule table (spec 06), merchant-overridable only within bounds:

    mode       R0    R1                      R2                                R3
    assisted   auto  approval                approval                          approval
    smart      auto  auto if conf ≥ thr      auto if enabled and conf ≥ thr    approval
    autopilot  auto  auto                    auto if enabled and conf ≥ thr    approval

Missing entitlement or capability → BLOCK. Above a merchant threshold → treated as R3. Confidence
below 0.5 (incomplete data) never auto-executes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import utcnow
from app.core.errors import PermissionDenied, ValidationFailed
from app.core.ids import uuid7
from app.domains.audit import service as audit
from app.domains.automation.models import AutomationActionLog, AutomationSettings, DecisionRecord
from app.domains.merchants.models import Merchant

MIN_CONFIDENCE = 0.5
# Defaults are deliberately conservative. Money in minor units (NPR paisa), percentages whole numbers.
DEFAULT_THRESHOLDS: dict[str, int] = {
    "refund_minor": 0,  # any automated refund needs approval unless raised
    "return_approve_minor": 150000,  # auto-approving returns worth up to Rs 1,500
    "discount_pct": 10,
    "discount_minor": 50000,
    "po_minor": 0,
    "campaign_budget_minor": 0,
    "stock_transfer_qty": 20,
    "price_change_pct": 5,
    "cod_verify_minor": 1000000,  # COD orders above Rs 10,000 need a phone check
}
# R2 actions a merchant may let run automatically. Opted in by default only where an earlier phase
# already behaved that way (delivery reattempts after the customer replied).
R2_ACTIONS = ("request_reattempt", "approve_return", "send_review_request")
DEFAULT_ENABLED_R2 = ["request_reattempt"]


def settings(db: Session, merchant_id: uuid.UUID) -> AutomationSettings:
    row = db.scalar(select(AutomationSettings).where(AutomationSettings.merchant_id == merchant_id))
    if row is not None:
        return row
    db.execute(
        pg_insert(AutomationSettings)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            confidence_threshold=0.8,
            thresholds=dict(DEFAULT_THRESHOLDS),
            enabled_r2=list(DEFAULT_ENABLED_R2),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["merchant_id"])
    )
    row = db.scalar(select(AutomationSettings).where(AutomationSettings.merchant_id == merchant_id))
    assert row is not None
    return row


def threshold(s: AutomationSettings, key: str) -> int:
    return int({**DEFAULT_THRESHOLDS, **(s.thresholds or {})}.get(key, 0))


def settings_view(s: AutomationSettings) -> dict[str, Any]:
    return {
        "confidence_threshold": s.confidence_threshold,
        "thresholds": {**DEFAULT_THRESHOLDS, **(s.thresholds or {})},
        "enabled_r2": list(s.enabled_r2 or []),
        "r2_actions": list(R2_ACTIONS),
    }


def update_settings(
    db: Session,
    ctx: TenantContext,
    *,
    thresholds: dict[str, int] | None,
    enabled_r2: list[str] | None,
    confidence_threshold: float | None,
) -> AutomationSettings:
    """Raising a limit, enabling an R2 action or lowering the confidence bar makes automation less
    safe: those need automation.approve and are audited as high-risk settings changes."""
    s = settings(db, ctx.merchant_id)
    before = settings_view(s)
    riskier = False
    if thresholds is not None:
        bad = [k for k in thresholds if k not in DEFAULT_THRESHOLDS]
        if bad or any(int(v) < 0 for v in thresholds.values()):
            raise ValidationFailed(code="threshold_invalid", details={"keys": bad})
        current = {**DEFAULT_THRESHOLDS, **(s.thresholds or {})}
        riskier |= any(int(v) > current[k] for k, v in thresholds.items())
        s.thresholds = {**current, **{k: int(v) for k, v in thresholds.items()}}
    if enabled_r2 is not None:
        bad = [a for a in enabled_r2 if a not in R2_ACTIONS]
        if bad:
            raise ValidationFailed(code="r2_action_invalid", details={"actions": bad})
        riskier |= bool(set(enabled_r2) - set(s.enabled_r2 or []))
        s.enabled_r2 = sorted(set(enabled_r2))
    if confidence_threshold is not None:
        riskier |= confidence_threshold < s.confidence_threshold
        s.confidence_threshold = confidence_threshold
    if riskier and not ctx.has("automation.approve"):
        raise PermissionDenied(
            "Only someone who can approve automation may loosen these limits",
            code="permission_denied",
            details={"permission": "automation.approve"},
        )
    after = settings_view(s)
    audit.record(
        db,
        action="automation.policy_loosened" if riskier else "automation.policy_updated",
        resource_type="merchant",
        resource_id=ctx.merchant_id,
        actor=ctx.actor,
        merchant_id=ctx.merchant_id,
        meta=ctx.meta,
        changes=audit.diff(before, after),
        metadata={"high_risk": riskier},
    )
    return s


# ----------------------------------------------------------------------------- decide
@dataclass
class Proposal:
    action: str
    risk_class: str  # R0…R4
    source: str  # workflow | inbox | recovery | returns
    confidence: float = 1.0
    impact_minor: int | None = None
    currency: str | None = None
    threshold_key: str | None = None
    entitled: bool = True
    capable: bool = True  # channel/provider capability present (e.g. a connected chat channel)
    # R2 opt-in owned by another policy (e.g. the returns policy's auto-approve). None = enabled_r2 list.
    enabled: bool | None = None
    inputs: dict[str, Any] = field(default_factory=dict)


def decide(db: Session, merchant_id: uuid.UUID, p: Proposal) -> DecisionRecord:
    merchant = db.get(Merchant, merchant_id)
    mode = merchant.automation_mode if merchant else "assisted"
    s = settings(db, merchant_id)
    thr = s.confidence_threshold
    risk = p.risk_class
    limit = threshold(s, p.threshold_key) if p.threshold_key else None
    vars_: dict[str, Any] = {"mode": mode, "confidence": round(p.confidence, 2)}
    if limit is not None:
        vars_["limit_minor"] = limit
    if p.impact_minor is not None:
        vars_["impact_minor"] = p.impact_minor

    if not p.entitled:
        decision, rule = "BLOCK", "missing_entitlement"
    elif not p.capable:
        decision, rule = "BLOCK", "missing_capability"
    elif risk == "R4":
        decision, rule = "BLOCK", "prohibited"
    elif limit is not None and p.impact_minor is not None and p.impact_minor > limit:
        decision, rule = "REQUIRE_APPROVAL", "above_threshold"
        risk = "R3"
    elif risk == "R3":
        decision, rule = "REQUIRE_APPROVAL", "high_risk"
    elif risk == "R0":
        decision, rule = "AUTO_EXECUTE", "informational"
    elif p.confidence < MIN_CONFIDENCE:
        decision, rule = "REQUIRE_APPROVAL", "low_confidence"
    elif mode == "assisted":
        decision, rule = "REQUIRE_APPROVAL", "assisted_mode"
    elif risk == "R1":
        if mode == "autopilot" or p.confidence >= thr:
            decision, rule = "AUTO_EXECUTE", f"{mode}_r1"
        else:
            decision, rule = "REQUIRE_APPROVAL", "below_confidence_threshold"
    else:  # R2
        enabled = p.enabled if p.enabled is not None else p.action in (s.enabled_r2 or [])
        if not enabled:
            decision, rule = "REQUIRE_APPROVAL", "r2_not_enabled"
        elif p.confidence < thr:
            decision, rule = "REQUIRE_APPROVAL", "below_confidence_threshold"
        else:
            decision, rule = "AUTO_EXECUTE", f"{mode}_r2_enabled"
    rec = DecisionRecord(
        id=uuid7(),
        merchant_id=merchant_id,
        source=p.source,
        action=p.action,
        risk_class=risk,
        decision=decision,
        rule=rule,
        mode=mode,
        confidence=p.confidence,
        financial_impact_minor=p.impact_minor,
        currency=p.currency,
        inputs=p.inputs,
        explanation={"rule": rule, "vars": vars_},
    )
    db.add(rec)
    db.flush()
    return rec


def resolve(db: Session, rec: DecisionRecord, outcome: str, user_id: uuid.UUID | None = None) -> None:
    rec.outcome, rec.resolved_at, rec.resolved_by_user_id = outcome, utcnow(), user_id


# ----------------------------------------------------------------------------- action log (AUT-018)
PERFORMER = {"user": "user", "staff": "user", "ai": "ai", "automation": "automation"}


def performed_by(actor: Actor) -> str:
    return PERFORMER.get(actor.type, "system")


def log_action(
    db: Session,
    merchant_id: uuid.UUID,
    capability: str,
    action: str,
    actor: Actor | str,
    *,
    key: str,
    resource_type: str | None = None,
    resource_id: Any = None,
    outcome: str = "success",
    eligible: bool = True,
    human_intervened: bool = False,
    exclusion_reason: str | None = None,
    decision_id: uuid.UUID | None = None,
) -> None:
    """Idempotent per (merchant, key): retries and redeliveries log once."""
    db.execute(
        pg_insert(AutomationActionLog)
        .values(
            id=uuid7(),
            merchant_id=merchant_id,
            capability=capability,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            eligible=eligible,
            performed_by=actor if isinstance(actor, str) else performed_by(actor),
            outcome=outcome,
            human_intervened=human_intervened,
            exclusion_reason=exclusion_reason,
            decision_id=decision_id,
            dedupe_key=key[:160],
            occurred_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["merchant_id", "dedupe_key"])
    )


def decision_view(d: DecisionRecord) -> dict[str, Any]:
    return {
        "id": d.id,
        "source": d.source,
        "action": d.action,
        "risk_class": d.risk_class,
        "decision": d.decision,
        "rule": d.rule,
        "mode": d.mode,
        "confidence": d.confidence,
        "impact": {"amount_minor": d.financial_impact_minor, "currency": d.currency}
        if d.financial_impact_minor is not None
        else None,
        "inputs": d.inputs,
        "explanation": d.explanation,
        "outcome": d.outcome,
        "created_at": d.created_at,
        "resolved_at": d.resolved_at,
    }
