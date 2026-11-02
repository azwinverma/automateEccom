"""Commercial-fact guard. AI copy must not state prices, discounts, stock, delivery promises,
warranties or authenticity/certification claims unless the seller supplied them. Violations are
reported (and the draft flagged for review) rather than silently rewritten."""

from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "price",
        re.compile(r"(?:\brs\.?|\bnpr\b|रू|रु\.?)\s*[\d०-९][\d०-९,]*|\b\d[\d,]*\s*(?:rs|rupees|npr)\b", re.I),
    ),
    ("discount", re.compile(r"\b\d{1,2}\s*%\s*(?:off|discount)|\bsale\b|छुट", re.I)),
    ("stock", re.compile(r"\bin stock\b|\bonly \d+ left\b|\blimited stock\b|\bsold out\b|स्टकमा", re.I)),
    (
        "delivery",
        re.compile(
            r"\bfree (?:delivery|shipping)\b|\bsame[- ]day delivery\b|\bdeliver(?:y|ed) in \d|"
            r"निःशुल्क डेलिभरी|फ्री डेलिभरी",
            re.I,
        ),
    ),
    ("warranty", re.compile(r"\bwarrant(?:y|ied)\b|\bguarantee[d]?\b|ग्यारेन्टी|वारेन्टी", re.I)),
    (
        "authenticity",
        re.compile(r"\b100\s*%\s*(?:original|genuine|pure|authentic)\b|\bcertified\b|\bauthentic\b", re.I),
    ),
]


@dataclass(frozen=True)
class Violation:
    field: str
    kind: str
    excerpt: str


def check(fields: dict[str, str], seller_notes: str = "") -> list[Violation]:
    """Flag claims in ``fields`` not supported by ``seller_notes`` (the seller's own words)."""
    notes = seller_notes.lower()
    out: list[Violation] = []
    for name, text in fields.items():
        for kind, pat in PATTERNS:
            for m in pat.finditer(text or ""):
                if m.group(0).lower() in notes:
                    continue
                out.append(Violation(name, kind, text[max(0, m.start() - 20) : m.end() + 20].strip()))
    return out
