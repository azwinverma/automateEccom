"""Creative attributes (CNT-012): structured description of every post/video so the Creative Genome
(Phase 7, specs/09) can learn which content actually sells.

Derived attributes are computed deterministically from the content itself (never guessed by a model):
language mix, caption length bucket, CTA type, local posting window, and video properties inherited
from Auto Reel jobs. Seller-declared attributes (hook type, human presence, background) are optional
and validated against controlled vocabularies; unknown stays ``unknown``/NULL rather than invented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

ATTRS_VERSION = 1
HOOK_TYPES = ("price_first", "product_closeup", "problem_solution", "social_proof", "offer", "unknown")
BACKGROUNDS = ("white", "lifestyle", "blurred_photo", "other")
LANGUAGE_MIXES = ("ne", "en", "ne_en_mixed", "none")
CTA_TYPES = ("dm", "comment", "link", "call", "none")
CAPTION_BUCKETS = ("short", "medium", "long")

_CTA_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("link", re.compile(r"https?://|\blink in bio\b|\bshop now\b|लिङ्क", re.I)),
    ("call", re.compile(r"\bcall\b|\bफोन\b|\+?977[\s-]?\d|\b9[78]\d{8}\b", re.I)),
    ("dm", re.compile(r"\bdm\b|\binbox\b|\bmessage (?:us|me)\b|\bmsg\b|म्यासेज|इनबक्स", re.I)),
    ("comment", re.compile(r"\bcomment\b|कमेन्ट", re.I)),
]


def language_mix(text: str) -> str:
    """Share of Devanagari vs Latin letters. Mixed when the minority script is ≥ 15% of letters."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "none"
    dev = sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters)
    if dev >= 0.85:
        return "ne"
    if dev <= 0.15:
        return "en"
    return "ne_en_mixed"


def caption_bucket(text: str) -> str:
    n = len(text.strip())
    return "short" if n < 80 else "long" if n > 300 else "medium"


def cta_type(text: str) -> str:
    for kind, pat in _CTA_PATTERNS:
        if pat.search(text):
            return kind
    return "none"


def posting_window(when: datetime | None, tz: str) -> int | None:
    """Merchant-local hour (0-23) the post is scheduled/published in; None if not scheduled."""
    return None if when is None else when.astimezone(ZoneInfo(tz)).hour


@dataclass(frozen=True)
class VideoAttrs:
    duration_s: float | None
    price_shown: bool
    price_timing_s: float | None
    template_id: str | None
    background: str | None
    hook_type: str


def from_video_job(duration_s: float | None, show_price: bool, template: str) -> VideoAttrs:
    """Auto Reel overlay is on screen for the whole video, so price timing is 0 s when shown."""
    return VideoAttrs(
        duration_s=duration_s,
        price_shown=show_price,
        price_timing_s=0.0 if show_price else None,
        template_id=f"auto_reel.{template}.v1",
        background="blurred_photo",
        hook_type="price_first" if show_price else "product_closeup",
    )
