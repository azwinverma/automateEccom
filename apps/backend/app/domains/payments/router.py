from __future__ import annotations

import uuid
from html import escape
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require
from app.core.config import get_settings
from app.core.context import TenantContext
from app.core.errors import ValidationFailed
from app.domains.orders import service as orders
from app.domains.payments import gateways, service
from app.domains.payments.models import Payment, PaymentGateway

router = APIRouter(tags=["payments"])
webhooks_router = APIRouter(tags=["webhooks"])
public_router = APIRouter(tags=["checkout"])  # customer-facing, no sign-in; links are HMAC-signed
log = structlog.get_logger(__name__)


class StartIn(BaseModel):
    return_url: str | None = Field(default=None, max_length=500)


class ManualIn(BaseModel):
    amount_minor: int = Field(gt=0, le=10_000_000_000, strict=True)
    method: str = Field(pattern=f"^({'|'.join(service.MANUAL_METHODS)})$")
    reference: str | None = Field(default=None, max_length=120)


@router.get("/orders/{order_id}/payments")
def list_payments(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    o = orders.get_order(db, ctx, order_id)
    rows = db.scalars(select(Payment).where(Payment.order_id == o.id).order_by(Payment.id))
    return {"items": [service.payment_view(p) for p in rows]}


@router.post("/orders/{order_id}/payments/online", status_code=201)
def start_online(
    order_id: uuid.UUID,
    body: StartIn,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """A payment link for the customer (prepaid orders). Paid only after server-side verification."""
    return service.payment_view(service.start_online_payment(db, ctx, order_id, body.return_url))


@router.post("/payments/{payment_id}/verify")
def verify(
    payment_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.read")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    p = db.get(Payment, payment_id)
    if p is None or p.merchant_id != ctx.merchant_id:
        from app.core.errors import NotFound

        raise NotFound(code="payment_not_found")
    return service.payment_view(service.verify(db, p.id))


@router.post("/orders/{order_id}/payments/manual", status_code=201)
def record_manual(
    order_id: uuid.UUID,
    body: ManualIn,
    ctx: TenantContext = Depends(require("payments.write")),
    db: Session = Depends(get_db, scope="function"),
    idem: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    if not idem:
        raise ValidationFailed(
            "Idempotency-Key header is required for recording payments", code="idempotency_key_required"
        )
    return service.payment_view(
        service.record_manual(
            db,
            ctx,
            order_id,
            amount_minor=body.amount_minor,
            method=body.method,
            reference=body.reference,
            key=idem,
        )
    )


@router.post("/orders/{order_id}/switch-to-cod")
def switch_to_cod(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require("orders.write")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return orders.order_view(db, service.switch_to_cod(db, ctx, order_id), detail=True)


@router.get("/payments/cod/summary")
def cod_summary(
    ctx: TenantContext = Depends(require("payments.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    return service.cod_summary(db, ctx)


@webhooks_router.post("/webhooks/payments/{provider}")
async def payment_webhook(provider: str, request: Request) -> JSONResponse:
    """Public, signature-verified. Records + dedupes, answers fast, verifies with the provider later."""
    from starlette.concurrency import run_in_threadpool

    body = await request.body()

    def _ingest() -> dict[str, int]:
        from app.core.db import session_scope

        with session_scope() as db:
            return service.ingest_payment_webhook(db, provider, dict(request.headers), body)

    try:
        stats = await run_in_threadpool(_ingest)
    except Exception as e:
        if getattr(e, "code", None) == "webhook_signature_invalid":
            return JSONResponse(
                {
                    "error": {
                        "code": "webhook_signature_invalid",
                        "message": "Invalid signature",
                        "details": {},
                        "request_id": request.state.request_id,
                    }
                },
                status_code=401,
            )
        raise
    return JSONResponse({"received": True, **stats})


# ----------------------------------------------------------------------------- seller's own gateways
class GatewayIn(BaseModel):
    provider: str = Field(pattern="^(khalti|esewa)$")
    mode: str = Field(default="test", pattern="^(test|live)$")
    secret_key: SecretStr = Field(min_length=8, max_length=200)
    public_id: str | None = Field(default=None, max_length=80)
    is_default: bool = False


@router.get("/payments/gateways/providers")
def gateway_providers(ctx: TenantContext = Depends(require("payments.read"))) -> dict[str, Any]:
    return {"items": gateways.catalog()}


@router.get("/payments/gateways")
def list_gateways(
    ctx: TenantContext = Depends(require("payments.read")), db: Session = Depends(get_db, scope="function")
) -> dict[str, Any]:
    rows = db.scalars(
        select(PaymentGateway)
        .where(PaymentGateway.status != "disconnected")
        .order_by(PaymentGateway.is_default.desc(), PaymentGateway.created_at)
    )
    return {"items": [gateways.view(g) for g in rows]}


@router.post("/payments/gateways", status_code=201)
def connect_gateway(
    body: GatewayIn,
    ctx: TenantContext = Depends(require("payments.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    """Connect (or replace the keys of) a gateway. The secret is sealed at once and never returned."""
    g = gateways.connect(
        db,
        ctx,
        provider=body.provider,
        mode=body.mode,
        secret_key=body.secret_key.get_secret_value(),
        public_id=body.public_id,
        make_default=body.is_default,
    )
    return gateways.view(g)


@router.post("/payments/gateways/{gateway_id}/test")
def test_gateway(
    gateway_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return gateways.view(gateways.test(db, ctx, gateway_id))


@router.post("/payments/gateways/{gateway_id}/default")
def default_gateway(
    gateway_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> dict[str, Any]:
    return gateways.view(gateways.set_default(db, ctx, gateway_id))


@router.delete("/payments/gateways/{gateway_id}", status_code=204)
def disconnect_gateway(
    gateway_id: uuid.UUID,
    ctx: TenantContext = Depends(require("payments.manage")),
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    gateways.disconnect(db, ctx, gateway_id)
    return Response(status_code=204)


# ----------------------------------------------------------------------------- customer checkout (public)
_PAGE_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action https://*.esewa.com.np; "
    "base-uri 'none'; frame-ancestors 'none'"
)
_CSS = (
    "body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;background:#f6f8fb;color:#0f172a;"
    "margin:0;display:grid;place-items:center;min-height:100vh}"
    "main{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:28px 24px;max-width:420px;"
    "width:calc(100% - 32px);box-sizing:border-box}"
    "h1{font-size:20px;margin:0 0 8px}p{margin:8px 0;line-height:1.5;color:#334155}"
    "button{font:inherit;font-weight:600;background:#0b5bd3;color:#fff;border:0;border-radius:10px;"
    "padding:12px 18px;width:100%;margin-top:12px;cursor:pointer}"
    ".ne{color:#475569;font-size:15px}small{color:#64748b}"
)
# key: (title, English line, Nepali line). {amount} is filled in.
_TEXT: dict[str, tuple[str, str, str]] = {
    "already_paid": ("Already paid", "{amount} was received. Thank you.", "भुक्तानी भइसकेको छ। धन्यवाद।"),
    "closed": (
        "This payment link is closed",
        "Please ask the shop for a new link.",
        "यो लिङ्क बन्द भयो। पसलसँग नयाँ लिङ्क माग्नुहोस्।",
    ),
    "unavailable": (
        "Payment is unavailable right now",
        "Please try again shortly or ask the shop.",
        "केही बेरपछि फेरि प्रयास गर्नुहोस् वा पसललाई सोध्नुहोस्।",
    ),
    "paid": (
        "Payment received",
        "{amount}. The shop will prepare your order.",
        "भुक्तानी प्राप्त भयो। पसलले अर्डर तयार गर्नेछ।",
    ),
    "needs_review": (
        "We're checking your payment",
        "The amount didn't match the order, so the shop will contact you.",
        "रकम नमिलेकाले पसलले सम्पर्क गर्नेछ।",
    ),
    "failed": (
        "Payment not completed",
        "No money was taken. You can try the link again.",
        "भुक्तानी पूरा भएन। फेरि प्रयास गर्न सक्नुहुन्छ।",
    ),
    "processing": (
        "Your payment is processing",
        "The shop will confirm as soon as the gateway does.",
        "गेटवेले पुष्टि गरेपछि पसलले जानकारी दिनेछ।",
    ),
}


def _page(title: str, body_html: str) -> HTMLResponse:
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex">'
        f"<title>{escape(title)}</title><style>{_CSS}</style></head><body><main>{body_html}</main></body></html>"
    )
    headers = {
        "Content-Security-Policy": _PAGE_CSP,
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
    }
    return HTMLResponse(html, headers=headers)


def _message(key: str, amount: str = "") -> HTMLResponse:
    title, en, ne = _TEXT[key]
    body = (
        f"<h1>{escape(title)}</h1><p>{escape(en.format(amount=amount))}</p>"
        f"<p class='ne' lang='ne'>{escape(ne)}</p>"
    )
    return _page(title, body)


def _amount(p: Payment) -> str:
    return f"Rs {p.amount_minor / 100:,.2f}"


def _load_public(db: Session, payment_id: uuid.UUID, t: str) -> Payment:
    from app.core.errors import NotFound

    if not service.link_token_ok(payment_id, t):
        raise NotFound(code="payment_not_found")
    p = db.scalar(select(Payment).where(Payment.id == payment_id).execution_options(skip_tenant_filter=True))
    if p is None or p.kind != "online":
        raise NotFound(code="payment_not_found")
    return p


@public_router.get("/pay/{payment_id}", include_in_schema=False)
def checkout(payment_id: uuid.UUID, t: str = "", db: Session = Depends(get_db, scope="function")) -> Response:
    """The customer's payment link. eSewa needs a signed form POSTed from the browser; we host it."""
    from app.domains.integrations.base import IntegrationError, Money

    p = _load_public(db, payment_id, t)
    if p.status == "paid":
        return _message("already_paid", _amount(p))
    if p.status != "pending":
        return _message("closed")
    try:
        adapter = service.adapter_for_payment(db, p)
        make_form = getattr(adapter, "checkout_form", None)
        form = (
            make_form(
                p.provider_payment_id, Money(p.amount_minor, p.currency), service.public_return_url(p.id)
            )
            if make_form
            else None
        )
    except IntegrationError:
        return _message("unavailable")
    if form is None:
        if p.redirect_url and not p.redirect_url.startswith(get_settings().public_api_base_url):
            return RedirectResponse(p.redirect_url, status_code=302)
        return _message("unavailable")
    action, fields = form
    inputs = "".join(
        f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">' for k, v in fields.items()
    )
    name = escape(adapter.display_name)
    amount = _amount(p)
    return _page(
        f"Pay {amount}",
        f"<h1>Pay {amount}</h1><p>You'll finish on {name}'s secure page.</p>"
        f"<p class='ne' lang='ne'>{name} को सुरक्षित पेजमा भुक्तानी गर्नुहोस्।</p>"
        f'<form method="post" action="{escape(action)}">{inputs}'
        f'<button type="submit">Continue to {name}</button></form>'
        "<p><small>Your payment details go to the gateway, never to the shop.</small></p>",
    )


@public_router.get("/pay/{payment_id}/return", include_in_schema=False)
def checkout_return(
    payment_id: uuid.UUID,
    t: str = "",
    data: str | None = None,
    db: Session = Depends(get_db, scope="function"),
) -> Response:
    """Where the gateway sends the customer back. We never trust the redirect: we ask the gateway."""
    p = _load_public(db, payment_id, t)
    if data and p.provider == "esewa":
        try:
            check = getattr(service.adapter_for_payment(db, p), "verify_return", None)
            if check is not None and check(data) is None:
                log.warning("esewa_return_signature_invalid", payment_id=str(p.id))
        except Exception:  # informational only; the status check below decides
            log.warning("esewa_return_unverifiable", payment_id=str(p.id))
    p = service.verify(db, p.id)
    key = {"paid": "paid", "needs_review": "needs_review", "failed": "failed"}.get(p.status, "processing")
    return _message(key, _amount(p))
