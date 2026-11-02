"""Catalog validation rules: SKU format/generation, GTIN barcode checksums, handles, money (CAT-009)."""

from __future__ import annotations

import re
import unicodedata

from app.core.errors import ValidationFailed

SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
HANDLE_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,118}[a-z0-9])?$")
MAX_PRICE_MINOR = (
    10_000_000_000  # NPR 100M in paisa — guards against unit mistakes (rupees entered as paisa: a 100x error)
)


def _field_error(field: str, message: str, code: str) -> ValidationFailed:
    return ValidationFailed(
        message, code=code, details={"fields": [{"loc": ["body", field], "msg": message}]}
    )


def normalize_sku(sku: str | None) -> str | None:
    if sku is None:
        return None
    s = sku.strip().upper().replace(" ", "-")
    if not s:
        return None
    if not SKU_RE.match(s):
        raise _field_error("sku", "SKU may use letters, numbers, '.', '-' and '_' (max 64)", "invalid_sku")
    return s


def _ascii_token(text: str, max_len: int) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    tok = re.sub(r"[^A-Z0-9]+", "-", norm.upper()).strip("-")
    return tok[:max_len].strip("-")


def generate_sku(handle: str, option_values: list[str], existing: set[str]) -> str:
    """Readable SKU from handle + option values: ``RED-KURTA-M``. Suffixes ``-2``.. on collision."""
    parts = [_ascii_token(handle, 24) or "ITEM"] + [
        _ascii_token(v, 10) for v in option_values if _ascii_token(v, 10)
    ]
    base = "-".join(parts)[:58]
    sku, n = base, 1
    while sku in existing:
        n += 1
        sku = f"{base}-{n}"
    return sku


def gtin_valid(code: str) -> bool:
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    check = digits.pop()
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


def normalize_barcode(barcode: str | None) -> str | None:
    """Numeric codes of GTIN length must have a valid checksum (catches typos before they reach
    marketplaces). Non-numeric internal codes are allowed (shop-printed labels)."""
    if barcode is None or not barcode.strip():
        return None
    b = barcode.strip().replace(" ", "")
    if b.isdigit() and len(b) in (8, 12, 13, 14):
        if not gtin_valid(b):
            raise _field_error(
                "barcode", "Barcode check digit is wrong — please re-scan or re-type it", "invalid_barcode"
            )
        return b
    if not re.fullmatch(r"[A-Za-z0-9-]{4,32}", b):
        raise _field_error("barcode", "Barcode must be 4-32 letters, numbers or '-'", "invalid_barcode")
    return b.upper()


def handleize(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")[:120]


def validate_handle(handle: str) -> str:
    if not HANDLE_RE.match(handle):
        raise _field_error(
            "handle", "Handle must be lowercase letters, numbers and hyphens", "invalid_handle"
        )
    return handle


def validate_money(field: str, value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0 or value > MAX_PRICE_MINOR:
        raise _field_error(field, "Amount is out of range", "invalid_amount")
    return value
