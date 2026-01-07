from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Iterable

from app.clients.jira_client import JiraClient
from app.core.config import settings
from app.core.errors import BadRequest, NotFound
from app.models.common import JiraSprint, SprintDetailsResponse, SprintListResponse
from app.utils.dates import SprintWindow, parse_ddmmyyyy, parse_jira_datetime


@lru_cache(maxsize=1)
def get_jira_client() -> JiraClient:
    return JiraClient()


def get_sprint_service() -> "SprintService":
    return SprintService(get_jira_client())


class SprintService:
    def __init__(self, jira: JiraClient) -> None:
        self._jira = jira
        self._log = logging.getLogger("app.sprints")

    async def get_sprint_by_id(self, sprint_id: int) -> SprintDetailsResponse:
        data = await self._jira.get_sprint(sprint_id)
        sprint = JiraSprint.model_validate(data)
        return SprintDetailsResponse(resolved_by="sprint_id", board_id=sprint.originBoardId, sprint=sprint)

    async def list_board_sprints(
        self, board_id: int, state: str, start_at: int, max_results: int
    ) -> SprintListResponse:
        payload = await self._jira.list_sprints(board_id=board_id, state=state, start_at=start_at, max_results=max_results)
        values = payload.get("values") or []
        sprints = [JiraSprint.model_validate(v) for v in values]
        return SprintListResponse(resolved_by="board_list", board_id=board_id, count=len(sprints), sprints=sprints)

    async def get_sprint_details(
        self,
        sprint_id: int | None,
        sprint_name: str | None,
        date: str | None,
        start_date: str | None,
        end_date: str | None,
        issue_key: str | None,
        mode: str,
        state: str,
    ) -> SprintDetailsResponse | SprintListResponse:
        # Validate at least one selector
        if not any([sprint_id, sprint_name, date, (start_date and end_date), issue_key]) and state != "active":
            raise BadRequest("Provide at least one of: sprint_id, sprint_name, issue_key, date, start_date+end_date, or set state=active")

        board_id = settings.jira_board_id

        # 1) sprint_id
        if sprint_id:
            return await self.get_sprint_by_id(sprint_id)

        # 2) issue_key
        if issue_key:
            return await self._resolve_by_issue_key(issue_key=issue_key, mode=mode)

        # 3-5 require listing sprints
        # reduce noise: if state param given, use it; else search all
        list_state = state if state != "all" else "all"
        all_sprints_raw = await self._jira.list_sprints_all_pages(board_id=board_id, state=list_state)
        all_sprints = [JiraSprint.model_validate(v) for v in all_sprints_raw]

        # 3) sprint_name
        if sprint_name:
            matches = self._match_by_name(all_sprints, sprint_name)
            return self._wrap(mode=mode, resolved_by="sprint_name", board_id=board_id, sprints=matches)

        # 4) single date
        if date:
            d = parse_ddmmyyyy(date, "date")
            matches = [s for s in all_sprints if self._sprint_window(s).contains_date(d)]
            return self._wrap(mode=mode, resolved_by="date", board_id=board_id, sprints=matches)

        # 5) date range
        if start_date and end_date:
            sd = parse_ddmmyyyy(start_date, "start_date")
            ed = parse_ddmmyyyy(end_date, "end_date")
            matches = [s for s in all_sprints if self._sprint_window(s).overlaps_range(sd, ed)]
            return self._wrap(mode=mode, resolved_by="date_range", board_id=board_id, sprints=matches)

        # 6) state=active fallback (common)
        if state == "active":
            active = [s for s in all_sprints if (s.state or "").lower() == "active"]
            return self._wrap(mode=mode, resolved_by="active", board_id=board_id, sprints=active)

        raise BadRequest("Unable to resolve sprint details with provided parameters")

    async def _resolve_by_issue_key(self, issue_key: str, mode: str) -> SprintDetailsResponse | SprintListResponse:
        raw = await self._jira.get_issue_sprint_field(issue_key)
        sprints: list[JiraSprint] = []

        # Jira may return list[dict] or list[str] or single dict; handle common forms.
        if raw is None:
            raise NotFound("No Sprint field found for issue", {"issue_key": issue_key})

        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    sprints.append(JiraSprint.model_validate(item))
                elif isinstance(item, str):
                    # Some Jira instances may return encoded string; try to extract sprint id like "id=123"
                    sid = _extract_sprint_id(item)
                    if sid:
                        data = await self._jira.get_sprint(sid)
                        sprints.append(JiraSprint.model_validate(data))
        elif isinstance(raw, dict):
            sprints.append(JiraSprint.model_validate(raw))
        elif isinstance(raw, str):
            sid = _extract_sprint_id(raw)
            if sid:
                data = await self._jira.get_sprint(sid)
                sprints.append(JiraSprint.model_validate(data))

        if not sprints:
            raise NotFound("Could not derive sprint(s) from issue", {"issue_key": issue_key})

        # De-dup by id
        uniq = {s.id: s for s in sprints}
        sprints = list(uniq.values())

        # Sort newest-ish
        sprints.sort(key=lambda s: self._sort_key(s), reverse=True)

        return self._wrap(mode=mode, resolved_by="issue_key", board_id=None, sprints=sprints)

    def _wrap(self, mode: str, resolved_by: str, board_id: int | None, sprints: list[JiraSprint]):
        if mode == "list":
            return SprintListResponse(resolved_by=resolved_by, board_id=board_id, count=len(sprints), sprints=sprints)
        # single
        if not sprints:
            raise NotFound("No sprint found for given criteria", {"resolved_by": resolved_by})
        return SprintDetailsResponse(resolved_by=resolved_by, board_id=board_id, sprint=sprints[0])

    def _match_by_name(self, sprints: list[JiraSprint], name: str) -> list[JiraSprint]:
        q = name.strip().lower()
        exact = [s for s in sprints if (s.name or "").strip().lower() == q]
        if exact:
            return sorted(exact, key=lambda s: self._sort_key(s), reverse=True)
        contains = [s for s in sprints if q in ((s.name or "").strip().lower())]
        return sorted(contains, key=lambda s: self._sort_key(s), reverse=True)

    def _sprint_window(self, sprint: JiraSprint) -> SprintWindow:
        return SprintWindow(
            start=parse_jira_datetime(sprint.startDate),
            end=parse_jira_datetime(sprint.endDate),
            complete=parse_jira_datetime(sprint.completeDate),
        )

    def _sort_key(self, sprint: JiraSprint):
        w = self._sprint_window(sprint)
        return w.effective_end or w.start or 0


def _extract_sprint_id(value: str) -> int | None:
    # common encoded form includes "id=123"
    import re
    m = re.search(r"\bid=(\d+)\b", value)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None
