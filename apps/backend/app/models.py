"""Imports every model module so SQLAlchemy metadata (Alembic autogenerate, mappers) is complete."""

from __future__ import annotations


def import_all() -> None:
    from app.domains.accounts import models as _accounts  # noqa: F401
    from app.domains.ai import models as _ai  # noqa: F401
    from app.domains.audit import models as _audit  # noqa: F401
    from app.domains.billing import models as _billing  # noqa: F401
    from app.domains.catalog import models as _catalog  # noqa: F401
    from app.domains.catalog import service as _catalog_service  # noqa: F401  (gauge counters)
    from app.domains.merchants import models as _merchants  # noqa: F401
    from app.domains.platform import models as _platform  # noqa: F401
