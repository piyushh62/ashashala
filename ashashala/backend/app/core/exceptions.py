import logging
import traceback
import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import settings

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with error code."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ExternalServiceError(AppError):
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service},
        )


def _json_safe_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip non-JSON-serializable bits from pydantic/FastAPI error dicts.

    Validators that raise a plain `ValueError` (e.g. our password-complexity
    check) get that exception object embedded verbatim under `ctx.error` —
    fine for `PydanticValidationError.errors(include_context=False)`, but
    `RequestValidationError.errors()` (raised for request-body validation,
    the far more common path) has no such option. Drop it unconditionally so
    both handlers can safely `json.dumps` the result; `msg` already carries
    the human-readable text.
    """
    safe = []
    for err in errors:
        err = dict(err)
        ctx = err.get("ctx")
        if isinstance(ctx, dict) and "error" in ctx:
            ctx = {k: v for k, v in ctx.items() if k != "error"}
            if ctx:
                err["ctx"] = ctx
            else:
                err.pop("ctx", None)
        safe.append(err)
    return safe


def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """Create standardized error response."""
    trace_id = trace_id or str(uuid.uuid4())[:8]
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "trace_id": trace_id,
            "details": details or {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "Application error: %s - %s (trace_id: %s)",
            exc.error_code,
            exc.message,
            getattr(request.state, "trace_id", "unknown"),
        )
        return create_error_response(
            request,
            exc.error_code,
            exc.message,
            exc.status_code,
            exc.details,
            getattr(request.state, "trace_id", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4())[:8])
        errors = _json_safe_errors(exc.errors())
        logger.warning("Validation error: %s (trace_id: %s)", errors, trace_id)
        return create_error_response(
            request,
            "VALIDATION_ERROR",
            "Request validation failed",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"errors": errors},
            trace_id,
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4())[:8])
        return create_error_response(
            request,
            "VALIDATION_ERROR",
            "Data validation failed",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"errors": _json_safe_errors(exc.errors())},
            trace_id,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4())[:8])
        logger.error("Database integrity error: %s (trace_id: %s)", exc, trace_id)
        return create_error_response(
            request,
            "CONFLICT",
            "Resource conflict — duplicate or constraint violation",
            status.HTTP_409_CONFLICT,
            trace_id=trace_id,
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4())[:8])
        logger.error("Database operational error: %s (trace_id: %s)", exc, trace_id)
        return create_error_response(
            request,
            "DATABASE_ERROR",
            "Database temporarily unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            trace_id=trace_id,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4())[:8])
        logger.exception("Unhandled exception (trace_id: %s): %s", trace_id, exc)
        if settings.LOG_LEVEL == "DEBUG":
            # In debug mode, include traceback
            return create_error_response(
                request,
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"traceback": traceback.format_exc()},
                trace_id,
            )
        return create_error_response(
            request,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            trace_id=trace_id,
        )