"""Operational CLI commands used by the runbooks (docs/runbooks). Every write is audited (actor: cli)."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.core.context import Actor
from app.core.db import bind_tenant, session_scope


def _audit(db: Any, action: str, meta: dict[str, Any]) -> None:
    from app.domains.audit import service as audit

    audit.record(
        db,
        action=action,
        resource_type="platform",
        resource_id=None,
        actor=Actor.system("cli"),
        merchant_id=None,
        metadata=meta,
    )


def _merchants(db: Any, slug: str | None) -> list[uuid.UUID]:
    from app.domains.merchants.models import Merchant

    stmt = select(Merchant.id).where(Merchant.status == "active").execution_options(skip_tenant_filter=True)
    if slug:
        stmt = stmt.where(Merchant.slug == slug)
    ids = list(db.scalars(stmt))
    if slug and not ids:
        raise SystemExit(f"merchant {slug} not found")
    return ids


def ops_status() -> dict[str, Any]:
    from prometheus_client import REGISTRY

    from app.domains.platform import ops

    ops.collect(force=True)
    wanted = {
        "outbox_pending_events",
        "outbox_oldest_pending_seconds",
        "outbox_dead_events",
        "webhook_events_unprocessed",
        "webhook_oldest_unprocessed_seconds",
        "webhook_events_dead",
        "channel_connections_need_attention",
        "listings_failed",
        "content_posts_failed",
        "refunds_failed",
        "cod_settlement_overdue",
        "shipments_stuck",
        "celery_queue_backlog",
        "twin_section_max_age_seconds",
        "product_brain_max_age_seconds",
        "data_quality_variants_without_cost_ratio",
        "recommendations_open",
        "job_last_success_timestamp_seconds",
    }
    out: dict[str, Any] = {}
    for fam in REGISTRY.collect():
        if fam.name not in wanted:
            continue
        for smp in fam.samples:
            key = smp.name + (
                "{" + ",".join(f"{k}={v}" for k, v in sorted(smp.labels.items())) + "}" if smp.labels else ""
            )
            out[key] = round(smp.value, 3)
    return dict(sorted(out.items()))


def run_ops(args: argparse.Namespace) -> None:
    if args.cmd == "ops-status":
        print(json.dumps(ops_status(), indent=2))  # noqa: T201
        return
    if args.cmd == "outbox-replay":
        from app.domains.platform.models import OutboxEvent
        from app.domains.platform.outbox import requeue

        with session_scope() as db:
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.status == args.status)
                .order_by(OutboxEvent.created_at)
                .limit(args.limit)
            )
            if args.event_type:
                stmt = stmt.where(OutboxEvent.event_type == args.event_type)
            if args.since:
                stmt = stmt.where(OutboxEvent.created_at >= datetime.fromisoformat(args.since))
            evs = list(db.scalars(stmt.execution_options(skip_tenant_filter=True)))
            by_type: dict[str, int] = {}
            for ev in evs:
                by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1
                if not args.dry_run:
                    requeue(db, ev.id)
            if not args.dry_run and evs:
                _audit(
                    db, "ops.outbox_replayed", {"count": len(evs), "by_type": by_type, "filter": vars(args)}
                )
            print(json.dumps({"dry_run": args.dry_run, "count": len(evs), "by_type": by_type}))  # noqa: T201
        return
    if args.cmd == "webhook-replay":
        from app.domains.channels.models import WebhookEvent
        from app.domains.channels.service import replay_webhook

        with session_scope() as db:
            wstmt = (
                select(WebhookEvent)
                .where(WebhookEvent.status == args.status)
                .order_by(WebhookEvent.received_at)
                .limit(args.limit)
            )
            if args.provider:
                wstmt = wstmt.where(WebhookEvent.provider == args.provider)
            wevs = list(db.scalars(wstmt))
            if not args.dry_run:
                for wev in wevs:
                    replay_webhook(db, wev.id)
                if evs:
                    _audit(
                        db,
                        "ops.webhooks_replayed",
                        {"count": len(evs), "status": args.status, "provider": args.provider},
                    )
            print(json.dumps({"dry_run": args.dry_run, "count": len(wevs)}))  # noqa: T201
        return
    if args.cmd in ("recompute-intelligence", "twin-reconcile"):
        part = "twin" if args.cmd == "twin-reconcile" else args.part
        stats: dict[str, Any] = {}
        with session_scope() as db:
            ids = _merchants(db, args.merchant)
        for mid in ids:
            with session_scope(mid) as db:
                bind_tenant(db, mid)
                stats[str(mid)] = _recompute(db, mid, part)
        with session_scope() as db:
            _audit(db, "ops.intelligence_recomputed", {"part": part, "merchants": len(ids)})
        print(json.dumps({"part": part, "merchants": len(ids), "results": stats}, default=str))  # noqa: T201
        return


def _recompute(db: Any, mid: uuid.UUID, part: str) -> dict[str, Any]:
    from app.domains.intelligence import (
        aps,
        courier_brain,
        creative,
        memory,
        product_brain,
        recommendations,
        return_intel,
    )
    from app.domains.procurement import supplier_intel
    from app.domains.twin import service as twin

    steps = {
        "courier": lambda: courier_brain.recompute(db, mid),
        "returns": lambda: return_intel.detect(db, mid),
        "product_brain": lambda: product_brain.recompute_merchant(db, mid),
        "memory": lambda: memory.compute(db, mid),
        "creative": lambda: creative.run(db, mid),
        "supplier": lambda: supplier_intel.compute(db, mid),
        "aps": lambda: aps.snapshot(db, mid).overall,
        "recommendations": lambda: recommendations.generate(db, mid),
        "twin": lambda: twin.reconcile(db, mid),
    }
    order = list(steps) if part == "all" else [part]
    out: dict[str, Any] = {}
    for name in order:
        try:
            with db.begin_nested():
                out[name] = steps[name]()
        except Exception as e:  # report and continue: one part failing mustn't stop the rest
            out[name] = f"error: {type(e).__name__}"
    return out
