"""Database engine, session, declarative base and tenant isolation.

Tenant isolation is enforced in two layers:
1. Every ``TenantScoped`` model carries a non-null ``merchant_id``. When a session is bound to a
   tenant (``bind_tenant``), all ORM SELECTs automatically get ``merchant_id = :tenant`` criteria
   (``with_loader_criteria``), so a forgotten filter cannot leak another merchant's rows.
2. A ``before_flush`` guard rejects inserting/updating a TenantScoped row whose merchant_id differs
   from the bound tenant.
Cross-tenant tests (tests/test_tenancy.py) exercise both layers.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, MetaData, create_engine, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    ORMExecuteState,
    Session,
    declared_attr,
    mapped_column,
    sessionmaker,
    with_loader_criteria,
)

from app.core.config import get_settings
from app.core.ids import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True), uuid.UUID: UUID(as_uuid=True)}


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)


class TenantScoped:
    """Mixin for every merchant-owned table."""

    @declared_attr
    def merchant_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), index=True, nullable=False)


class TenantViolation(RuntimeError):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_engine(
            s.database_url,
            pool_size=s.database_pool_size,
            max_overflow=s.database_max_overflow,
            pool_pre_ping=True,
            # Never embed bound parameters (emails, hashes, tokens) in exception messages/logs.
            hide_parameters=True,
            connect_args={"options": f"-c statement_timeout={s.database_statement_timeout_ms}"},
        )
    return _engine


def session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)
    return _SessionLocal


def reset_engine() -> None:
    """Testing hook: drop cached engine after settings change."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope(tenant_id: uuid.UUID | None = None) -> Iterator[Session]:
    """Unit of work for workers/scripts. Commits on success, rolls back on error."""
    db = session_factory()()
    if tenant_id is not None:
        bind_tenant(db, tenant_id)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def bind_tenant(db: Session, tenant_id: uuid.UUID) -> None:
    db.info["tenant_id"] = tenant_id


def current_tenant(db: Session) -> uuid.UUID | None:
    return db.info.get("tenant_id")


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_criteria(state: ORMExecuteState) -> None:
    tenant_id = state.session.info.get("tenant_id")
    if tenant_id is None or not state.is_select or state.execution_options.get("skip_tenant_filter"):
        return
    state.statement = state.statement.options(
        with_loader_criteria(TenantScoped, lambda cls: cls.merchant_id == tenant_id, include_aliases=True)
    )


@event.listens_for(Session, "before_flush")
def _guard_tenant_writes(session: Session, _ctx: Any, _instances: Any) -> None:
    tenant_id = session.info.get("tenant_id")
    if tenant_id is None:
        return
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, TenantScoped):
            mid = obj.merchant_id
            if mid is None:
                obj.merchant_id = tenant_id
            elif mid != tenant_id:
                raise TenantViolation(f"{type(obj).__name__} merchant_id does not match bound tenant")
