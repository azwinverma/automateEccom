"""Keyset (cursor) pagination over UUIDv7 primary keys (time ordered)."""

from __future__ import annotations

import base64
import uuid
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import Select

from app.core.errors import ValidationFailed

T = TypeVar("T")
MAX_LIMIT = 200


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None


def encode_cursor(last_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(last_id.bytes).decode().rstrip("=")


def decode_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(bytes=base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    except (ValueError, TypeError) as e:
        raise ValidationFailed("Invalid cursor", details={"fields": [{"loc": ["cursor"]}]}) from e


def paginate_desc(stmt: Select, id_col, limit: int, cursor: str | None) -> Select:
    limit = max(1, min(limit, MAX_LIMIT))
    if cursor:
        stmt = stmt.where(id_col < decode_cursor(cursor))
    return stmt.order_by(id_col.desc()).limit(limit + 1)


def build_page(rows: list, limit: int, id_getter=lambda r: r.id) -> tuple[list, str | None]:
    limit = max(1, min(limit, MAX_LIMIT))
    has_more = len(rows) > limit
    rows = rows[:limit]
    return rows, (encode_cursor(id_getter(rows[-1])) if has_more and rows else None)
