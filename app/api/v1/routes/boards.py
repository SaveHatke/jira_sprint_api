from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.models.common import ApiError, SprintListResponse
from app.services.sprint_service import SprintService, get_sprint_service

router = APIRouter(prefix="/boards")


@router.get(
    "/{board_id}/sprints",
    response_model=SprintListResponse,
    responses={400: {"model": ApiError}, 401: {"model": ApiError}, 404: {"model": ApiError}, 502: {"model": ApiError}},
)
async def list_board_sprints(
    board_id: int,
    state: str = Query(default="all", pattern="^(active|future|closed|all)$"),
    startAt: int = Query(default=0, ge=0),
    maxResults: int = Query(default=50, ge=1, le=200),
    svc: SprintService = Depends(get_sprint_service),
):
    return await svc.list_board_sprints(board_id=board_id, state=state, start_at=startAt, max_results=maxResults)
