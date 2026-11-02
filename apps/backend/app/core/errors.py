"""Application error hierarchy mapped to the API error envelope (docs/api/phase-0-contract.md)."""

from __future__ import annotations

import traceback
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    message = "Bad request"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        self.headers = headers or {}
        super().__init__(self.message)


class ValidationFailed(AppError):
    status_code = 400
    code = "validation_error"
    message = "Validation failed"


class NotAuthenticated(AppError):
    status_code = 401
    code = "not_authenticated"
    message = "Authentication required"


class PermissionDenied(AppError):
    status_code = 403
    code = "permission_denied"
    message = "You do not have permission to perform this action"


class FeatureNotInPlan(AppError):
    status_code = 403
    code = "feature_not_in_plan"
    message = "This feature is not included in the current plan"


class UsageLimitReached(AppError):
    status_code = 402
    code = "usage_limit_reached"
    message = "Usage limit reached for this billing period"


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    message = "Not found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    message = "Conflict"


class InvalidStateTransition(AppError):
    status_code = 422
    code = "invalid_state_transition"
    message = "Invalid state transition"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests"


class DependencyUnavailable(AppError):
    status_code = 503
    code = "dependency_unavailable"
    message = "A dependency is temporarily unavailable"


def _envelope(request: Request, code: str, message: str, details: dict[str, Any]) -> dict[str, Any]:
    request.state.error_code = code  # surfaced in the access log for operations
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            log.warning("app_error", code=exc.code, status=exc.status_code)
        return JSONResponse(
            _envelope(request, exc.code, exc.message, exc.details),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(
            _envelope(request, "validation_error", "Validation failed", {"fields": fields}), status_code=400
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(_envelope(request, code, str(exc.detail), {}), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, DBAPIError):
            # Postgres echoes row values in messages (e.g. unique-violation DETAIL), so log only
            # structured, value-free facts plus stack frames.
            diag = getattr(getattr(exc, "orig", None), "diag", None)
            log.error(
                "unhandled_db_error",
                error_type=type(exc).__name__,
                sqlstate=getattr(diag, "sqlstate", None),
                constraint=getattr(diag, "constraint_name", None),
                table=getattr(diag, "table_name", None),
                frames=[
                    f"{f.filename}:{f.lineno} {f.name}" for f in traceback.extract_tb(exc.__traceback__)[-8:]
                ],
            )
        else:
            log.exception("unhandled_error", error_type=type(exc).__name__)
        return JSONResponse(
            _envelope(request, "internal_error", "Something went wrong on our side", {}), status_code=500
        )
