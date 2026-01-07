from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from app.core.config import settings
from app.core.errors import BadRequest, NotFound, Unauthorized, UpstreamError
from app.core.logging import get_request_id


_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


class JiraClient:
    def __init__(self) -> None:
        self._log = logging.getLogger("app.jira")
        self._timeout = httpx.Timeout(settings.http_timeout_seconds)
        self._client = httpx.AsyncClient(base_url=str(settings.jira_base_url).rstrip("/"), timeout=self._timeout)
        self._cache_enabled = settings.cache_enabled
        self._cache = TTLCache(maxsize=settings.cache_maxsize, ttl=settings.cache_ttl_seconds) if self._cache_enabled else None

    def _auth_headers(self) -> dict[str, str]:
        scheme = (settings.jira_auth_scheme or "bearer").lower()
        if scheme == "bearer":
            return {"Authorization": f"Bearer {settings.jira_pat}"}
        if scheme == "basic":
            if not settings.jira_username:
                raise BadRequest("JIRA_USERNAME is required for basic auth")
            import base64
            token = base64.b64encode(f"{settings.jira_username}:{settings.jira_pat}".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        raise BadRequest("Unsupported JIRA_AUTH_SCHEME", {"scheme": scheme})

    def _headers(self) -> dict[str, str]:
        return {
            **self._auth_headers(),
            "Accept": "application/json",
            "User-Agent": "jira-sprint-api/0.1.0",
            "X-Request-ID": get_request_id(),
        }

    async def close(self) -> None:
        await self._client.aclose()

    def _cache_get(self, key: str):
        if not self._cache_enabled or self._cache is None:
            return None
        return self._cache.get(key)

    def _cache_set(self, key: str, val: Any) -> None:
        if not self._cache_enabled or self._cache is None:
            return
        self._cache[key] = val

    @retry(
        retry=retry_if_exception_type(UpstreamError),
        stop=stop_after_attempt(settings.http_max_retries),
        wait=wait_random_exponential(min=settings.http_backoff_min_seconds, max=settings.http_backoff_max_seconds),
        reraise=True,
    )
    async def _request(self, method: str, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            resp = await self._client.request(method, url, headers=self._headers(), params=params)
        except httpx.TimeoutException as e:
            raise UpstreamError("Jira request timed out", {"url": url}) from e
        except httpx.RequestError as e:
            raise UpstreamError("Jira request failed", {"url": url}) from e
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            self._log.info("jira_http", extra={"extra": {"method": method, "url": url, "duration_ms": dur_ms}})

        if resp.status_code in _TRANSIENT_STATUS:
            raise UpstreamError("Transient Jira error", {"status_code": resp.status_code, "url": url})
        if resp.status_code in (401, 403):
            raise Unauthorized("Jira authentication/authorization failed", {"status_code": resp.status_code})
        if resp.status_code == 404:
            raise NotFound("Jira resource not found", {"url": url})
        if resp.status_code >= 400:
            raise UpstreamError("Jira returned error", {"status_code": resp.status_code, "url": url, "body": safe_text(resp.text)})

        return resp.json()

    async def get_sprint(self, sprint_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/rest/agile/1.0/sprint/{sprint_id}")

    async def list_sprints(self, board_id: int, state: str = "all", start_at: int = 0, max_results: int = 50) -> dict[str, Any]:
        params = {"startAt": start_at, "maxResults": max_results}
        if state != "all":
            params["state"] = state
        return await self._request("GET", f"/rest/agile/1.0/board/{board_id}/sprint", params=params)

    async def list_sprints_all_pages(self, board_id: int, state: str = "all") -> list[dict[str, Any]]:
        cache_key = f"sprints:{board_id}:{state}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        start_at = 0
        page_size = 50
        all_values: list[dict[str, Any]] = []
        while True:
            payload = await self.list_sprints(board_id=board_id, state=state, start_at=start_at, max_results=page_size)
            values = payload.get("values") or []
            all_values.extend(values)
            is_last = payload.get("isLast", False)
            if is_last:
                break
            start_at = int(payload.get("startAt", start_at)) + int(payload.get("maxResults", page_size))
            # safety
            if start_at > 10000:
                break

        self._cache_set(cache_key, all_values)
        return all_values

    async def get_fields(self) -> list[dict[str, Any]]:
        cache_key = "fields"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        fields = await self._request("GET", "/rest/api/2/field")
        if not isinstance(fields, list):
            raise UpstreamError("Unexpected Jira fields response")
        self._cache_set(cache_key, fields)
        return fields

    async def discover_sprint_field_id(self) -> str:
        cache_key = "sprint_field_id"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        fields = await self.get_fields()
        for f in fields:
            name = (f.get("name") or "").strip().lower()
            if name == "sprint":
                fid = f.get("id")
                if fid:
                    self._cache_set(cache_key, fid)
                    return fid
        # fallback: try partial match
        for f in fields:
            name = (f.get("name") or "").strip().lower()
            if "sprint" == name:
                fid = f.get("id")
                if fid:
                    self._cache_set(cache_key, fid)
                    return fid
        raise NotFound("Could not discover 'Sprint' field id in Jira")

    async def get_issue_sprint_field(self, issue_key: str) -> Any:
        sprint_fid = await self.discover_sprint_field_id()
        payload = await self._request("GET", f"/rest/api/2/issue/{issue_key}", params={"fields": sprint_fid})
        fields = (payload or {}).get("fields") or {}
        return fields.get(sprint_fid)


def safe_text(s: str, limit: int = 800) -> str:
    s = s or ""
    s = s.replace("\n", " ").replace("\r", " ")
    return s[:limit]
