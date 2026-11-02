"""Prompt registry (AIG-012). Built-in prompts are versioned in code; an ``active`` PromptTemplate row
in the database (same name + locale) overrides them without a deploy. Every AI execution records the
prompt name + version it used, so evals and incidents can be traced to exact prompt text."""

from __future__ import annotations

from dataclasses import dataclass
from string import Template
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.ai.models import PromptTemplate


@dataclass(frozen=True)
class Prompt:
    name: str
    version: int
    system: str
    user: str  # string.Template with $placeholders (safe: no attribute access, no format-string tricks)
    schema: dict[str, Any] | None = None

    def render_user(self, **params: str) -> str:
        return Template(self.user).safe_substitute(**params)


_BUILTIN: dict[str, Prompt] = {}


def register(p: Prompt) -> Prompt:
    _BUILTIN[p.name] = p
    return p


def get_prompt(db: Session | None, name: str, locale: str = "en") -> Prompt:
    if db is not None:
        row = db.scalar(
            select(PromptTemplate).where(
                PromptTemplate.name == name,
                PromptTemplate.locale == locale,
                PromptTemplate.rollout_state == "active",
            )
        )
        if row is not None:
            return Prompt(row.name, row.version, row.system_template, row.user_template, row.output_schema)
    try:
        return _BUILTIN[name]
    except KeyError as e:
        raise KeyError(f"prompt {name!r} is not registered") from e
