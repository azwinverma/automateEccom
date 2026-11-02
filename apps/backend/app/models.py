"""Imports every model module so SQLAlchemy metadata (Alembic autogenerate, mappers) is complete."""

from __future__ import annotations


def import_all() -> None:
    from app.domains.accounts import models as _accounts  # noqa: F401
    from app.domains.ai import models as _ai  # noqa: F401
    from app.domains.audit import models as _audit  # noqa: F401
    from app.domains.billing import models as _billing  # noqa: F401
    from app.domains.catalog import models as _catalog  # noqa: F401
    from app.domains.catalog import service as _catalog_service  # noqa: F401  (gauge counters)
    from app.domains.channels import models as _channels  # noqa: F401
    from app.domains.channels import service as _channels_service  # noqa: F401  (gauge, handlers)
    from app.domains.media import models as _media  # noqa: F401
    from app.domains.media import service as _media_service  # noqa: F401  (gauge, handler)
    from app.domains.merchants import models as _merchants  # noqa: F401
    from app.domains.platform import models as _platform  # noqa: F401
    from app.domains.studio import models as _studio  # noqa: F401
