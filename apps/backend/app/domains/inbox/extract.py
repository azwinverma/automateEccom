"""Deterministic understanding of chat messages (English, Romanized Nepali, Devanagari).

Runs on every message, with or without an AI key. The AI gateway's intent model only fills fields
these rules couldn't find, and only when it's confident. Phone numbers, districts and wards are never
taken from the model when a rule found them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.domains.customers import nepal

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_INTENT_WORDS: list[tuple[str, tuple[str, ...]]] = [
    ("human", ("human", "real person", "manager", "call me", "talk to someone", "मान्छे", "फोन गर्नु")),
    (
        "complaint",
        (
            "complain",
            "complaint",
            "broken",
            "damaged",
            "torn",
            "fake",
            "worst",
            "bad quality",
            "bigriyo",
            "fateko",
            "bigreko",
            "फाटेको",
            "बिग्रियो",
            "गुनासो",
        ),
    ),
    ("refund", ("refund", "money back", "paisa firta", "पैसा फिर्ता")),
    ("return", ("return", "firta", "फिर्ता")),
    ("exchange", ("exchange", "change size", "saatna", "साट्न")),
    ("cancellation", ("cancel", "रद्द")),
    (
        "order_status",
        ("where is my order", "order status", "kaha pugyo", "kahile aaucha", "track", "कहाँ पुग्यो", "कहिले आउँछ"),
    ),
    ("payment", ("esewa", "khalti", "fonepay", "bank", "qr", "payment", "भुक्तानी")),
    ("delivery", ("delivery", "deliver", "shipping", "kati din", "डेलिभरी")),
    ("price", ("price", "kati", "how much", "rate", "cost", "मूल्य", "कति", "रेट")),
    ("size", ("size", "fit", "साइज")),
    ("stock", ("available", "in stock", "stock", "cha?", "chha", "पाइन्छ", "छ?")),
    (
        "order",
        (
            "order",
            "buy",
            "chahiyo",
            "chaiyo",
            "book",
            "i want",
            "i'll take",
            "pathaidinu",
            "चाहियो",
            "अर्डर",
            "पठाइदिनु",
        ),
    ),
    ("greeting", ("hello", "hi ", "namaste", "namaskar", "नमस्ते", "नमस्कार")),
]
_YES = re.compile(
    r"^\s*(yes|y|ok|okay|confirm|confirmed|sure|ho|hajur|huncha|hunchha|thik cha|done|हो|हजुर|हुन्छ|ठिक छ|पक्का)\b",
    re.I,
)
_NO = re.compile(r"^\s*(no|n|cancel|hoina|pardaina|chaidaina|होइन|पर्दैन|चाहिँदैन)\b", re.I)
_COD = re.compile(r"\b(cod|cash|cash on delivery|delivery ma|aaye pachi)\b|नगद", re.I)
_PREPAID = re.compile(r"\b(prepaid|online|esewa|khalti|fonepay|bank|qr)\b", re.I)
_WARD = re.compile(r"(?:ward|wada|वडा)\s*(?:no\.?|number|नं\.?)?\s*[-:]?\s*(\d{1,2})", re.I)
_QTY = re.compile(
    r"(?:\b|x)(\d{1,2})\s*(?:pcs|pc|piece|pieces|wota|ota|ta|vata|wata|वटा|ओटा)\b|\bx\s?(\d{1,2})\b", re.I
)


@dataclass
class Extracted:
    intent: str | None = None
    phone: str | None = None
    district: str | None = None
    ward: int | None = None
    quantity: int | None = None
    payment: str | None = None
    yes: bool = False
    no: bool = False
    locale: str = "en"
    words: list[str] = field(default_factory=list)


def understand(text: str) -> Extracted:
    t = text.translate(_DEV_DIGITS)
    low = f" {t.lower()} "
    e = Extracted(locale="ne" if DEVANAGARI.search(text) else "en")
    for intent, words in _INTENT_WORDS:
        if any(w in low for w in words):
            e.intent = intent
            break
    e.phone = nepal.find_phone(t)
    without_phone = re.sub(r"(?:\+?977[-\s]?)?9[678][\d\s-]{8,12}", " ", t)
    for code, (name, _prov) in nepal.DISTRICTS.items():
        if re.search(rf"\b{re.escape(name.lower())}\b", low):
            e.district = code
            break
    if (m := _WARD.search(without_phone)) and 1 <= int(m.group(1)) <= nepal.MAX_WARD:
        e.ward = int(m.group(1))
    if m := _QTY.search(without_phone):
        q = int(m.group(1) or m.group(2))
        e.quantity = q if 1 <= q <= 50 else None
    if _COD.search(t):
        e.payment = "cod"
    elif _PREPAID.search(t):
        e.payment = "prepaid"
    e.yes, e.no = bool(_YES.search(t)), bool(_NO.search(t))
    e.words = [w for w in re.findall(r"[\wऀ-ॿ]+", t.lower()) if len(w) >= 2]
    return e


def option_match(text: str, value: str) -> bool:
    """Does the customer's message mention this option value ("XL", "Black", "कालो")?"""
    return bool(re.search(rf"(?<![\w]){re.escape(value.lower())}(?![\w])", text.lower()))
