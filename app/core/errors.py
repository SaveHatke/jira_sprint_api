from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_request_id


@dataclass
class AppError(Exception):
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None


class BadRequest(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(400, "bad_request", message, details)


class Unauthorized(AppError):
    def __init__(self, message: str = "Unauthorized", details: dict[str, Any] | None = None):
        super().__init__(401, "unauthorized", message, details)


class NotFound(AppError):
    def __init__(self, message: str = "Not found", details: dict[str, Any] | None = None):
        super().__init__(404, "not_found", message, details)


class UpstreamError(AppError):
    def __init__(self, message: str = "Upstream error", details: dict[str, Any] | None = None):
        super().__init__(502, "upstream_error", message, details)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logging.getLogger("app").warning(
            "app_error",
            extra={
                "request_id": get_request_id(),
                "code": exc.code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details or {},
                    "correlation_id": get_request_id(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logging.getLogger("app").exception(
            "unhandled_error",
            extra={"request_id": get_request_id(), "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": {},
                    "correlation_id": get_request_id(),
                }
            },
        )
