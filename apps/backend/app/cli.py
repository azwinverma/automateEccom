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
    elif args.cmd == "dispatch-outbox":
        import app.domains.handlers  # noqa: F401
        from app.domains.platform.outbox import dispatch_batch

        print(json.dumps(dispatch_batch()))  # noqa: T201


if __name__ == "__main__":
    main()
