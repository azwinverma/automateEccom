"""Deterministic scorers for AI evals (AIG-015). Each returns (score 0..1, notes)."""

from __future__ import annotations

from typing import Any

import jsonschema

from app.domains.studio import grounding
from app.domains.studio.schema import EXTRACTION_SCHEMA, LIMITS

Score = tuple[float, list[str]]


def _devanagari_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters) if letters else 0.0


def schema_valid(out: dict[str, Any], case: dict[str, Any]) -> Score:
    try:
        jsonschema.validate(out, EXTRACTION_SCHEMA)
        return 1.0, []
    except jsonschema.ValidationError as e:
        return 0.0, [f"schema: {e.message[:120]}"]


def grounded(out: dict[str, Any], case: dict[str, Any]) -> Score:
    fields = {
        "title_en": out.get("title_en", ""),
        "description_en": out.get("description_en", ""),
        "title_ne": out.get("title_ne", ""),
        "description_ne": out.get("description_ne", ""),
        **{f"captions.{k}": v for k, v in (out.get("captions") or {}).items()},
    }
    v = grounding.check(fields, case.get("notes", ""))
    return (1.0 if not v else 0.0), [f"claim:{x.kind} in {x.field}: {x.excerpt}" for x in v]


def nepali_is_nepali(out: dict[str, Any], case: dict[str, Any]) -> Score:
    """Nepali fields must be mostly Devanagari (catches English copy pasted into *_ne)."""
    ratios = [_devanagari_ratio(out.get(f, "")) for f in ("title_ne", "description_ne")]
    ok = [r >= 0.6 for r in ratios]
    return sum(ok) / len(ok), [
        f"{f} only {r:.0%} Devanagari"
        for f, r, good in zip(("title_ne", "description_ne"), ratios, ok, strict=True)
        if not good
    ]


def within_limits(out: dict[str, Any], case: dict[str, Any]) -> Score:
    notes = [
        f"{f} too long"
        for f in ("title_en", "title_ne", "description_en", "description_ne")
        if len(out.get(f) or "") > LIMITS[f]
    ]
    if len(out.get("hashtags") or []) > LIMITS["hashtags"]:
        notes.append("too many hashtags")
    return (1.0 if not notes else 0.0), notes


def expected_category(out: dict[str, Any], case: dict[str, Any]) -> Score:
    want = [w.lower() for w in case.get("expect", {}).get("category_contains", [])]
    if not want:
        return 1.0, []
    path = " / ".join((out.get("category") or {}).get("path", [])).lower()
    hits = [w for w in want if w in path]
    return len(hits) / len(want), [f"category missing '{w}' (got '{path}')" for w in want if w not in hits]


def attribute_accuracy(out: dict[str, Any], case: dict[str, Any]) -> Score:
    want: dict[str, str] = case.get("expect", {}).get("attributes", {})
    if not want:
        return 1.0, []
    got = {a.get("key", "").lower(): a.get("value", "").lower() for a in out.get("attributes") or []}
    hits = [k for k, v in want.items() if v.lower() in got.get(k, "")]
    return len(hits) / len(want), [
        f"attribute {k}: expected '{v}', got '{got.get(k)}'" for k, v in want.items() if k not in hits
    ]


def never_invents_options(out: dict[str, Any], case: dict[str, Any]) -> Score:
    """Sizes must never be invented when the seller didn't mention them."""
    if case.get("expect", {}).get("sizes_known"):
        return 1.0, []
    invented = [
        o for o in out.get("suggested_options") or [] if o.get("name", "").lower() in ("size", "sizes")
    ]
    return (0.0, ["invented size option"]) if invented else (1.0, [])


SCORERS = {
    "schema_valid": schema_valid,
    "grounded": grounded,
    "nepali_is_nepali": nepali_is_nepali,
    "within_limits": within_limits,
    "expected_category": expected_category,
    "attribute_accuracy": attribute_accuracy,
    "never_invents_options": never_invents_options,
}
# Hard gates: a single failure fails the case regardless of the average.
GATES = ("schema_valid", "grounded")
