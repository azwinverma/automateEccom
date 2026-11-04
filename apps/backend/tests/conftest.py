"""Test fixtures. Integration tests run against real PostgreSQL and Redis (no SQLite/fakes), because
tenancy criteria, row locks, partial unique indexes and triggers are what we are testing."""

from __future__ import annotations

import os

os.environ.setdefault("COS_ENVIRONMENT", "test")
os.environ.setdefault("COS_DATABASE_URL", "postgresql+psycopg://localhost:5432/commerce_os_test")
os.environ.setdefault("COS_REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("COS_LOG_LEVEL", "WARNING")

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.db import get_engine, session_scope
from app.core.redis import get_redis

BACKEND = Path(__file__).resolve().parents[1]
CATALOG_TABLES = {
    "alembic_version",
    "billing_features",
    "billing_resources",
    "billing_plans",
    "billing_plan_versions",
    "billing_plan_entitlements",
    "billing_plan_limits",
    "billing_addons",
}
PASSWORD = "Correct-Horse-Battery-9"


def _ensure_database(url: str) -> None:
    u = make_url(url)
    admin = sa.create_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(sa.text(f'DROP DATABASE IF EXISTS "{u.database}" WITH (FORCE)'))
        c.execute(sa.text(f'CREATE DATABASE "{u.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _celery_eager() -> None:
    """Run Celery tasks inline so outbox → task → AI gateway flows are testable without a broker."""
    from app.worker.celery_app import celery

    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    url = get_settings().database_url
    _ensure_database(url)
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")
    from app.domains.billing.plans import seed_from_file
    from app.models import import_all

    import_all()
    with session_scope() as db:
        seed_from_file(db)
    yield
    get_engine().dispose()


@pytest.fixture(autouse=True)
def _clean() -> Iterator[None]:
    yield
    with get_engine().begin() as conn:
        tables = [
            r[0]
            for r in conn.execute(sa.text("select tablename from pg_tables where schemaname='public'"))
            if r[0] not in CATALOG_TABLES
        ]
        conn.execute(sa.text("SET session_replication_role = replica"))  # bypass audit immutability trigger
        conn.execute(sa.text(f"TRUNCATE {', '.join(tables)} CASCADE"))
        conn.execute(sa.text("SET session_replication_role = DEFAULT"))
    get_redis().flushdb()
    from app.domains.ai.providers.sandbox import SandboxAdapter

    SandboxAdapter.failures.clear()
    SandboxAdapter.override_data.clear()
    from app.domains.integrations.sandbox import SandboxChannelAdapter

    SandboxChannelAdapter.failures.clear()
    SandboxChannelAdapter.published.clear()
    SandboxChannelAdapter.stock.clear()
    SandboxChannelAdapter.orders.clear()
    SandboxChannelAdapter.sent.clear()
    from app.domains.integrations.sandbox import SandboxPaymentAdapter

    SandboxPaymentAdapter.paid_amounts.clear()
    SandboxChannelAdapter.revoked_refresh_tokens.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@dataclass
class Seller:
    client: TestClient
    email: str
    token: str
    refresh: str
    user_id: str
    merchant_id: str | None = None

    def h(self, merchant: str | None = None, **extra: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.token}", **extra}
        mid = merchant or self.merchant_id
        if mid:
            headers["X-Merchant-Id"] = mid
        return headers


def register_and_login(client: TestClient, email: str | None = None, name: str = "Sita Shrestha") -> Seller:
    email = email or f"seller-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": name,
            "phone": "+977 9801234567",
            "locale": "ne",
        },
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD, "device_name": "pytest"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return Seller(
        client, email, body["access_token"], body["refresh_token"], r.json().get("session_id", ""), None
    )


def onboard(client: TestClient, email: str | None = None, shop: str = "Thamel Threads") -> Seller:
    s = register_and_login(client, email)
    r = client.post(
        "/api/v1/merchants",
        headers=s.h(),
        json={"name": shop, "currency": "NPR", "timezone": "Asia/Kathmandu", "default_locale": "ne"},
    )
    assert r.status_code == 201, r.text
    s.merchant_id = r.json()["id"]
    return s


@pytest.fixture
def seller(client: TestClient) -> Seller:
    return onboard(client)


def set_plan(merchant_id: str, plan_code: str) -> None:
    """Move a merchant's live subscription to another plan's active version (test helper)."""
    from sqlalchemy import select

    from app.domains.billing.models import Plan, PlanVersion, Subscription

    with session_scope() as db:
        pv = db.scalar(
            select(PlanVersion)
            .join(Plan, Plan.id == PlanVersion.plan_id)
            .where(Plan.code == plan_code, PlanVersion.status == "active")
        )
        sub = db.scalar(select(Subscription).where(Subscription.merchant_id == uuid.UUID(merchant_id)))
        assert pv is not None and sub is not None
        sub.plan_version_id = pv.id
        sub.status = "active"
