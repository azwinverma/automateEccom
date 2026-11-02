"""Request context middleware: request id, trace span, structured access log, metrics, security headers."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Mapping
from typing import Any

import structlog
from opentelemetry import propagate, trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import HTTP_LATENCY, HTTP_REQUESTS
from app.core.tracing import tracer

log = structlog.get_logger("access")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")
_SKIP_LOG = {"/healthz", "/readyz", "/metrics"}


def route_template(scope: Mapping[str, Any]) -> str:
    """Full route template (e.g. /api/v1/stores/{store_id}) for bounded-cardinality metric labels.

    Starlette >= 1.0 reports routes relative to their router mount, so the mount prefix is recovered by
    rendering the template with the matched params and stripping it from the concrete path.
    """
    route = scope.get("route")
    tpl = getattr(route, "path", None)
    if tpl is None:
        return "unmatched"
    path: str = scope.get("path", "")
    rendered = tpl
    for k, v in (scope.get("path_params") or {}).items():
        rendered = re.sub(r"\{" + re.escape(k) + r"(:[^}]*)?\}", str(v), rendered)
    prefix = path[: -len(rendered)] if rendered and path.endswith(rendered) else ""
    return prefix + tpl


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        ctx = propagate.extract(dict(request.headers))
        start = time.perf_counter()
        status = 500
        with tracer().start_as_current_span(
            f"{request.method} {request.url.path}", context=ctx, kind=trace.SpanKind.SERVER
        ) as span:
            sc = span.get_span_context()
            if sc.is_valid:
                structlog.contextvars.bind_contextvars(trace_id=format(sc.trace_id, "032x"))
            try:
                response = await call_next(request)
                status = response.status_code
            finally:
                route_tpl = route_template(request.scope)
                elapsed = time.perf_counter() - start
                HTTP_REQUESTS.labels(request.method, route_tpl, str(status)).inc()
                HTTP_LATENCY.labels(request.method, route_tpl).observe(elapsed)
                span.set_attribute("http.route", route_tpl)
                span.set_attribute("http.status_code", status)
                if request.url.path not in _SKIP_LOG:
                    log.info(
                        "request",
                        method=request.method,
                        route=route_tpl,
                        status=status,
                        duration_ms=round(elapsed * 1000, 1),
                        merchant_id=getattr(request.state, "merchant_id", None),
                        user_id=getattr(request.state, "user_id", None),
                        error_code=getattr(request.state, "error_code", None),
                    )
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response
