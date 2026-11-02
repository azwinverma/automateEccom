"""Routing policy loader. Default policy is a versioned JSON contract; DB overrides (ADM-009) later."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.domains.ai.types import Capability


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str
    effort: str | None = None


@dataclass(frozen=True)
class TaskPolicy:
    task: str
    capability: Capability
    feature: str | None
    usage_resource: str | None
    timeout_s: float
    max_attempts_per_candidate: int
    candidates: tuple[Candidate, ...]
    min_confidence: float | None = None


@dataclass(frozen=True)
class RoutingPolicy:
    tasks: dict[str, TaskPolicy]
    pricing: dict[str, dict[str, Any]]
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)
    breaker_failure_threshold: int = 5
    breaker_window_s: int = 60
    breaker_open_s: int = 30
    retry_base_delay_s: float = 0.5
    retry_max_delay_s: float = 8.0

    def task(self, name: str) -> TaskPolicy:
        try:
            return self.tasks[name]
        except KeyError as e:
            raise KeyError(f"AI task {name!r} is not defined in the routing policy") from e

    def price(self, provider: str, model: str) -> dict[str, Any] | None:
        return self.pricing.get(f"{provider}:{model}")


def parse_policy(doc: dict[str, Any]) -> RoutingPolicy:
    tasks = {}
    for name, t in doc["tasks"].items():
        tasks[name] = TaskPolicy(
            task=name,
            capability=Capability(t["capability"]),
            feature=t.get("feature"),
            usage_resource=t.get("usage_resource"),
            timeout_s=float(t["timeout_s"]),
            max_attempts_per_candidate=int(t.get("max_attempts_per_candidate", 2)),
            candidates=tuple(Candidate(c["provider"], c["model"], c.get("effort")) for c in t["candidates"]),
            min_confidence=t.get("min_confidence"),
        )
    cb, rt = doc.get("circuit_breaker", {}), doc.get("retry", {})
    return RoutingPolicy(
        tasks=tasks,
        pricing=doc.get("pricing", {}),
        providers=doc.get("providers", {}),
        breaker_failure_threshold=cb.get("failure_threshold", 5),
        breaker_window_s=cb.get("window_s", 60),
        breaker_open_s=cb.get("open_s", 30),
        retry_base_delay_s=rt.get("base_delay_s", 0.5),
        retry_max_delay_s=rt.get("max_delay_s", 8.0),
    )


@lru_cache
def load_policy(path: Path | None = None) -> RoutingPolicy:
    p = path or get_settings().ai_routing_policy_path
    return parse_policy(json.loads(Path(p).read_text()))
