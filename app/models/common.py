from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiErrorItem(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""


class ApiError(BaseModel):
    error: ApiErrorItem


class JiraSprint(BaseModel):
    id: int
    self: str | None = None
    state: str | None = None
    name: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    completeDate: str | None = None
    originBoardId: int | None = None
    goal: str | None = None


class SprintDetailsResponse(BaseModel):
    mode: Literal["single"] = "single"
    resolved_by: str
    board_id: int | None = None
    sprint: JiraSprint


class SprintListResponse(BaseModel):
    mode: Literal["list"] = "list"
    resolved_by: str
    board_id: int | None = None
    count: int
    sprints: list[JiraSprint]
