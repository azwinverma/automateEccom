from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.tracing import configure_tracing
from app.models import import_all

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    configure_tracing(settings)
    import_all()

    app = FastAPI(
        title="Nivaro API",
        summary="Nivaro — Autonomous Commerce OS. Seller, channel and admin API.",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None if settings.is_production_like else f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Merchant-Id", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Idempotent-Replayed", "Retry-After"],
    )
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    from app.domains.accounts.router import router as accounts
    from app.domains.admin.router import router as admin
    from app.domains.ai.router import router as ai
    from app.domains.audit.router import router as audit
    from app.domains.automation.router import router as automation
    from app.domains.billing.router import router as billing
    from app.domains.catalog.router import router as catalog
    from app.domains.channels.router import admin_router as webhooks_admin
    from app.domains.channels.router import dev_router as channels_dev
    from app.domains.channels.router import listings_router, webhooks_router
    from app.domains.channels.router import router as channels
    from app.domains.content.router import router as content
    from app.domains.customers.router import router as customers
    from app.domains.exceptions.router import router as exceptions
    from app.domains.fulfillment.router import dev_router as fulfillment_dev
    from app.domains.fulfillment.router import router as fulfillment
    from app.domains.fulfillment.router import webhooks_router as courier_webhooks
    from app.domains.inbox.router import router as inbox
    from app.domains.intelligence.router import router as intelligence
    from app.domains.inventory.router import router as inventory
    from app.domains.media.router import dev_router as media_dev
    from app.domains.media.router import router as media
    from app.domains.merchants.router import router as merchants
    from app.domains.orders.router import router as orders
    from app.domains.payments.router import router as payments
    from app.domains.payments.router import webhooks_router as payment_webhooks
    from app.domains.platform.router import health_router
    from app.domains.platform.router import router as platform
    from app.domains.returns.router import router as returns
    from app.domains.studio.router import router as studio

    app.include_router(health_router)
    app.include_router(media_dev)
    app.include_router(channels_dev)
    # Payment webhooks first: /webhooks/payments/{provider} must not be read as a channel's
    # /webhooks/{provider}/{connection_id}.
    app.include_router(payment_webhooks)
    app.include_router(courier_webhooks)  # /webhooks/couriers/{provider}/{account_id}
    app.include_router(webhooks_router)  # public: signature-verified, no user auth
    for r in (
        accounts,
        merchants,
        billing,
        catalog,
        listings_router,
        media,
        studio,
        channels,
        content,
        customers,
        inventory,
        orders,
        inbox,
        payments,
        fulfillment,
        fulfillment_dev,  # dev-only simulator; each route 404s in staging/production
        returns,
        automation,
        intelligence,
        exceptions,
        audit,
        platform,
        ai,
        admin,
        webhooks_admin,
    ):
        app.include_router(r, prefix=API_PREFIX)
    return app


app = create_app()
