"""
Stable error envelope for the INFONET API.

Every application error (except the health endpoint's status-in-body 200
response) must use this envelope.  FastAPI validation exceptions are
converted to 422 INVALID_PARAMETER with this shape.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ── Error codes ──

NOT_FOUND = "NOT_FOUND"
INVALID_PARAMETER = "INVALID_PARAMETER"
INTERNAL_ERROR = "INTERNAL_ERROR"
DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
DATA_NOT_LOADED = "DATA_NOT_LOADED"


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Return a JSONResponse using the stable error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Convert FastAPI/Pydantic validation errors to 422 INVALID_PARAMETER."""
    # Extract the first invalid parameter name for `details.parameter`
    first_error = exc.errors()[0] if exc.errors() else {}
    loc = first_error.get("loc", ())
    param_name = str(loc[-1]) if loc else "unknown"

    return error_response(
        status_code=422,
        code=INVALID_PARAMETER,
        message=f"Invalid value for parameter '{param_name}'.",
        details={"parameter": param_name},
    )
