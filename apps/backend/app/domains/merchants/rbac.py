"""Role-based access control. Permissions are fine-grained strings; system roles map to sets.

Business code checks permissions (``orders.write``), never role names. Permissions for domains that
are not built yet are declared now so role semantics stay stable as modules land.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


DOMAIN_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "merchant": ("read", "update"),
    "store": ("read", "create", "update"),
    "team": ("read", "manage"),
    "billing": ("read", "manage"),
    "audit": ("read",),
    "settings": ("manage",),
    "ai": ("use", "credentials.manage"),
    "channels": ("read", "manage"),
    "catalog": ("read", "write", "publish"),
    "media": ("read", "write"),
    "content": ("read", "write", "approve", "publish"),
    "customers": ("read", "write", "merge", "export"),
    "inbox": ("read", "reply", "assign"),
    "orders": ("read", "write", "cancel"),
    "inventory": ("read", "adjust", "transfer"),
    "procurement": ("read", "write", "approve"),
    "payments": ("read", "write", "manage"),
    "fulfillment": ("read", "write"),
    "returns": ("read", "write", "approve"),
    "refunds": ("read", "create", "approve"),
    "marketing": ("read", "write"),
    "automation": ("read", "write", "approve"),
    "analytics": ("read",),
}

ALL_PERMISSIONS: frozenset[str] = frozenset(
    f"{domain}.{action}" for domain, actions in DOMAIN_PERMISSIONS.items() for action in actions
)


def _perms(*patterns: str) -> frozenset[str]:
    out: set[str] = set()
    for p in patterns:
        if p.endswith(".*"):
            prefix = p[:-1]
            out |= {perm for perm in ALL_PERMISSIONS if perm.startswith(prefix)}
        elif p.startswith("*."):
            suffix = p[1:]
            out |= {perm for perm in ALL_PERMISSIONS if perm.endswith(suffix)}
        else:
            if p not in ALL_PERMISSIONS:
                raise ValueError(f"Unknown permission {p}")
            out.add(p)
    return frozenset(out)


_OPERATIONAL = (
    "catalog.read",
    "catalog.write",
    "catalog.publish",
    "media.read",
    "media.write",
    "content.read",
    "content.write",
    "content.publish",
    "customers.read",
    "customers.write",
    "inbox.read",
    "inbox.reply",
    "inbox.assign",
    "orders.read",
    "orders.write",
    "orders.cancel",
    "inventory.read",
    "inventory.adjust",
    "inventory.transfer",
    "payments.read",
    "fulfillment.read",
    "fulfillment.write",
    "returns.read",
    "returns.write",
    "refunds.read",
    "refunds.create",
    "marketing.read",
    "marketing.write",
    "automation.read",
    "analytics.read",
    "procurement.read",
    "procurement.write",
    "channels.read",
    "ai.use",
    "merchant.read",
    "store.read",
    "team.read",
)

ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.OWNER: ALL_PERMISSIONS,
    # Admin: everything except billing management (owner-only money decisions).
    Role.ADMIN: ALL_PERMISSIONS - {"billing.manage"},
    Role.MANAGER: _perms(
        *_OPERATIONAL,
        "content.approve",
        "returns.approve",
        "refunds.approve",
        "automation.write",
        "automation.approve",
        "procurement.approve",
        "customers.merge",
        "customers.export",
        "payments.write",
        "billing.read",
        "audit.read",
        "channels.manage",
        "store.update",
        "team.manage",
    ),
    Role.STAFF: _perms(
        "merchant.read",
        "store.read",
        "team.read",
        "catalog.read",
        "catalog.write",
        "media.read",
        "media.write",
        "content.read",
        "content.write",
        "customers.read",
        "customers.write",
        "inbox.read",
        "inbox.reply",
        "orders.read",
        "orders.write",
        "inventory.read",
        "fulfillment.read",
        "fulfillment.write",
        "returns.read",
        "returns.write",
        "refunds.read",
        # Staff may raise refunds; above the merchant's threshold (default: all) a manager approves.
        "refunds.create",
        "payments.read",
        "ai.use",
        "channels.read",
    ),
    Role.VIEWER: _perms("*.read"),
}

# Roles a given role may assign. Prevents privilege escalation via invitations/role changes.
ASSIGNABLE_ROLES: dict[Role, frozenset[Role]] = {
    Role.OWNER: frozenset(Role),
    Role.ADMIN: frozenset({Role.ADMIN, Role.MANAGER, Role.STAFF, Role.VIEWER}),
    Role.MANAGER: frozenset({Role.STAFF, Role.VIEWER}),
    Role.STAFF: frozenset(),
    Role.VIEWER: frozenset(),
}


def permissions_for(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(Role(role), frozenset())
