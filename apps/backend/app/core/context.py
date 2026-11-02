"""Per-request actor context passed into services (who, which tenant, from where)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Actor:
    type: str  # user | system | automation | ai | staff | webhook
    id: uuid.UUID | None = None
    display: str | None = None

    @staticmethod
    def system(name: str = "system") -> Actor:
        return Actor(type="system", display=name)


@dataclass(frozen=True)
class RequestMeta:
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    source: str = "api"
    trace_id: str | None = None


@dataclass(frozen=True)
class TenantContext:
    merchant_id: uuid.UUID
    actor: Actor
    role: str | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)
    meta: RequestMeta = field(default_factory=RequestMeta)

    def has(self, permission: str) -> bool:
        return permission in self.permissions
