from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging, RequestIdMiddleware

configure_logging()

app = FastAPI(
    title="Jira Sprint API",
    version="0.1.0",
)

# CORS: off by default; enable explicitly via env if you want (kept minimal here)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIdMiddleware)

app.include_router(api_router)

install_exception_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    # Minimal readiness: confirm config present; optionally ping Jira if enabled
    return {
        "status": "ok",
        "jira_base_url": settings.jira_base_url,
        "default_board_id": settings.jira_board_id,
    }
