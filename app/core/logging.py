from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_ctx.get() or ""


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        logging.getLogger("app.access").info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": getattr(response, "status_code", None),
                "duration_ms": duration_ms,
            },
        )
        return response


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "lvl": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": get_request_id(),
        }
        extra = {}
        for k, v in getattr(record, "__dict__", {}).items():
            if k in {"args", "msg", "levelname", "levelno", "name", "pathname", "filename", "module",
                     "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                     "relativeCreated", "thread", "threadName", "processName", "process"}:
                continue
            if k.startswith("_"):
                continue
            extra[k] = v
        # merge record.extra if present
        if isinstance(extra.get("extra"), dict):
            merged = {**base, **extra["extra"]}
        else:
            merged = {**base, **extra}
        # compact key=value output
        parts = [f"{k}={repr(v)}" for k, v in merged.items() if v not in (None, "", [])]
        return " ".join(parts)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler()
    handler.setLevel(root.level)
    handler.setFormatter(KeyValueFormatter())

    # Replace handlers (avoid duplicates in reload)
    root.handlers = [handler]

    # quieter
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
