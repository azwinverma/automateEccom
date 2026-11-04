"""Operational CLI: `python -m app.cli <command>`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.db import session_scope
from app.models import import_all


def main() -> None:
    import_all()
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("seed-plans", help="Load/upgrade plans from the entitlements contract (idempotent)")
    sp.add_argument("--file", type=Path, default=None)
    st = sub.add_parser("make-staff", help="Grant platform staff to an existing user (requires MFA to use)")
    st.add_argument("email")
    sub.add_parser("dispatch-outbox", help="Run one outbox dispatch batch")
    pl = sub.add_parser(
        "set-plan", help="Move a merchant to another plan (ops/support until the plan editor ships)"
    )
    pl.add_argument("merchant_slug")
    pl.add_argument("plan_code")
    ev = sub.add_parser("run-evals", help="Run an AI eval suite and write a JSON report")
    ev.add_argument("suite")
    ev.add_argument("--threshold", type=float, default=0.85)
    args = p.parse_args()

    if args.cmd == "seed-plans":
        from app.domains.billing.plans import DEFAULT_PATH, seed_from_file

        with session_scope() as db:
            print(json.dumps(seed_from_file(db, args.file or DEFAULT_PATH)))  # noqa: T201
    elif args.cmd == "make-staff":
        from app.domains.accounts.service import find_user_by_email

        with session_scope() as db:
            u = find_user_by_email(db, args.email)
            if u is None:
                raise SystemExit("user not found")
            u.is_platform_staff = True
            from app.core.context import Actor
            from app.domains.audit import service as audit

            audit.record(
                db,
                action="admin.staff_granted",
                resource_type="user",
                resource_id=u.id,
                actor=Actor.system("cli"),
                merchant_id=None,
            )
            print("ok")  # noqa: T201
    elif args.cmd == "run-evals":
        from datetime import UTC, datetime

        from app.domains.ai.evals.runner import EVALS_DIR, run

        report = run(args.suite, args.threshold)
        out = EVALS_DIR / "reports" / f"{args.suite}-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        summary = {k: report[k] for k in ("mean_score", "providers", "sandbox_only", "passed")}
        print(json.dumps(summary | {"report": str(out)}))  # noqa: T201
        if report["sandbox_only"]:
            print("NOTE: sandbox provider answered; this validates the harness, not model quality.")  # noqa: T201
        raise SystemExit(0 if report["passed"] or report["sandbox_only"] else 1)
    elif args.cmd == "set-plan":
        from sqlalchemy import select

        from app.core.context import Actor
        from app.domains.audit import service as audit
        from app.domains.billing.models import Plan, PlanVersion, Subscription
        from app.domains.merchants.models import Merchant

        with session_scope() as db:
            m = db.scalar(select(Merchant).where(Merchant.slug == args.merchant_slug))
            pv = db.scalar(
                select(PlanVersion)
                .join(Plan, Plan.id == PlanVersion.plan_id)
                .where(Plan.code == args.plan_code, PlanVersion.status == "active")
            )
            if m is None or pv is None:
                raise SystemExit("merchant or plan not found")
            sub_row = db.scalar(
                select(Subscription)
                .where(Subscription.merchant_id == m.id)
                .execution_options(skip_tenant_filter=True)
            )
            if sub_row is None:
                raise SystemExit("merchant has no subscription")
            before = str(sub_row.plan_version_id)
            sub_row.plan_version_id, sub_row.status = pv.id, "active"
            audit.record(
                db,
                action="billing.plan_changed_by_ops",
                resource_type="subscription",
                resource_id=sub_row.id,
                actor=Actor.system("cli"),
                merchant_id=m.id,
                metadata={"plan": args.plan_code, "previous_plan_version": before},
            )
        print(json.dumps({"merchant": args.merchant_slug, "plan": args.plan_code}))  # noqa: T201
    elif args.cmd == "dispatch-outbox":
        import app.domains.handlers  # noqa: F401
        from app.domains.platform.outbox import dispatch_batch

        print(json.dumps(dispatch_batch()))  # noqa: T201


if __name__ == "__main__":
    main()
