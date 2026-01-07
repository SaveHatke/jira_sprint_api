from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.models.common import ApiError, SprintDetailsResponse, SprintListResponse
from app.services.sprint_service import SprintService, get_sprint_service

router = APIRouter(prefix="/sprints")


@router.get(
    "/details",
    response_model=SprintDetailsResponse | SprintListResponse,
    responses={400: {"model": ApiError}, 401: {"model": ApiError}, 404: {"model": ApiError}, 502: {"model": ApiError}},
)
async def sprint_details(
    sprint_id: int | None = Query(default=None, ge=1),
    sprint_name: str | None = Query(default=None, min_length=1),
    date: str | None = Query(default=None, description="DDMMYYYY"),
    start_date: str | None = Query(default=None, description="DDMMYYYY"),
    end_date: str | None = Query(default=None, description="DDMMYYYY"),
    issue_key: str | None = Query(default=None, min_length=1),
    mode: str = Query(default="single", pattern="^(single|list)$"),
    state: str = Query(default="all", pattern="^(active|future|closed|all)$"),
    svc: SprintService = Depends(get_sprint_service),
):
    """Smart sprint details endpoint (no 'resolve' keyword)."""
    return await svc.get_sprint_details(
        sprint_id=sprint_id,
        sprint_name=sprint_name,
        date=date,
        start_date=start_date,
        end_date=end_date,
        issue_key=issue_key,
        mode=mode,
        state=state,
    )


@router.get(
    "/{sprint_id}",
    response_model=SprintDetailsResponse,
    responses={400: {"model": ApiError}, 401: {"model": ApiError}, 404: {"model": ApiError}, 502: {"model": ApiError}},
)
async def get_sprint_by_id(
    sprint_id: int,
    svc: SprintService = Depends(get_sprint_service),
):
    return await svc.get_sprint_by_id(sprint_id)
