"""Eval runner: ``python -m app.cli run-evals product_extraction [--threshold 0.85]``.

Cases live in ``apps/backend/evals/<suite>/*.json``. Each case lists photo files (relative to the
case file), optional seller notes and expectations. Without a provider key the gateway falls back to
the sandbox provider, which validates the harness but not model quality — reports say which provider
answered so a sandbox run is never mistaken for a quality measurement.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domains.ai.evals.scorers import GATES, SCORERS
from app.domains.ai.gateway import AIUnavailable, gateway
from app.domains.ai.prompts import get_prompt
from app.domains.ai.types import AIRequest, ImageInput, Message

EVALS_DIR = Path(__file__).resolve().parents[4] / "evals"


def load_cases(suite: str) -> list[tuple[Path, dict[str, Any]]]:
    return [(p, json.loads(p.read_text())) for p in sorted((EVALS_DIR / suite).glob("*.json"))]


def _request(case_path: Path, case: dict[str, Any]) -> AIRequest:
    import app.domains.studio.prompts  # noqa: F401  (registers prompt)

    prompt = get_prompt(None, "studio.product_extraction")
    images = []
    for rel in case.get("photos", []):
        f = case_path.parent / rel
        images.append(
            ImageInput(
                media_type=mimetypes.guess_type(f.name)[0] or "image/jpeg",
                data_b64=base64.b64encode(f.read_bytes()).decode(),
            )
        )
    return AIRequest(
        system=prompt.system,
        json_schema=prompt.schema,
        max_tokens=6000,
        locale=case.get("locale", "ne"),
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        messages=(
            Message(
                "user",
                prompt.render_user(
                    notes=case.get("notes") or "(none)",
                    locale=case.get("locale", "ne"),
                    brand_voice=case.get("brand_voice", "warm and friendly; at most one or two emoji"),
                ),
                tuple(images),
            ),
        ),
    )


def score_output(out: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    results = {name: fn(out, case) for name, fn in SCORERS.items()}
    gates_ok = all(results[g][0] == 1.0 for g in GATES)
    avg = statistics.mean(s for s, _ in results.values())
    return {
        "score": round(avg if gates_ok else 0.0, 3),
        "gates_passed": gates_ok,
        "scores": {k: round(v[0], 3) for k, v in results.items()},
        "notes": [n for _, notes in results.values() for n in notes],
    }


def run(suite: str, threshold: float = 0.85) -> dict[str, Any]:
    cases = load_cases(suite)
    report: dict[str, Any] = {"suite": suite, "started_at": datetime.now(UTC).isoformat(), "cases": []}
    providers = set()
    for path, case in cases:
        try:
            res = gateway.run(
                task="PRODUCT_EXTRACTION",
                request=_request(path, case),
                merchant_id=None,
                idempotency_key=f"eval:{suite}:{case['id']}:{datetime.now(UTC).timestamp()}",
            )
        except AIUnavailable as e:
            report["cases"].append({"id": case["id"], "score": 0.0, "error": e.code})
            continue
        providers.add(f"{res.provider}:{res.model}")
        report["cases"].append(
            {
                "id": case["id"],
                "provider": f"{res.provider}:{res.model}",
                "cost_usd_micros": res.cost_usd_micros,
                "latency_ms": res.latency_ms,
                **score_output(dict(res.data), case),
            }
        )
    scores = [c["score"] for c in report["cases"]]
    report["mean_score"] = round(statistics.mean(scores), 3) if scores else 0.0
    report["providers"] = sorted(providers)
    report["sandbox_only"] = bool(providers) and all(p.startswith("sandbox") for p in providers)
    report["threshold"] = threshold
    report["passed"] = (not report["sandbox_only"]) and report["mean_score"] >= threshold
    return report
