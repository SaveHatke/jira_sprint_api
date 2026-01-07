from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from app.core.errors import BadRequest


def parse_ddmmyyyy(value: str, field_name: str) -> dt.date:
    if not value:
        raise BadRequest(f"{field_name} is required")
    if len(value) != 8 or not value.isdigit():
        raise BadRequest(f"{field_name} must be in DDMMYYYY format", {"field": field_name, "value": value})
    day = int(value[0:2])
    month = int(value[2:4])
    year = int(value[4:8])
    try:
        return dt.date(year, month, day)
    except ValueError:
        raise BadRequest(f"{field_name} is not a valid date", {"field": field_name, "value": value})


def parse_jira_datetime(value: str | None) -> Optional[dt.datetime]:
    if not value:
        return None
    # Jira usually returns ISO 8601 with timezone, e.g., 2025-01-07T10:00:00.000+05:30
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True)
class SprintWindow:
    start: Optional[dt.datetime]
    end: Optional[dt.datetime]
    complete: Optional[dt.datetime]

    @property
    def effective_end(self) -> Optional[dt.datetime]:
        # for closed sprints, complete may be more meaningful if end missing
        return self.end or self.complete

    def contains_date(self, date_: dt.date) -> bool:
        if not self.start or not self.effective_end:
            return False
        d0 = dt.datetime.combine(date_, dt.time.min, tzinfo=self.start.tzinfo)
        d1 = dt.datetime.combine(date_, dt.time.max, tzinfo=self.start.tzinfo)
        return self.start <= d1 and self.effective_end >= d0

    def overlaps_range(self, start_date: dt.date, end_date: dt.date) -> bool:
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        if not self.start or not self.effective_end:
            return False
        r0 = dt.datetime.combine(start_date, dt.time.min, tzinfo=self.start.tzinfo)
        r1 = dt.datetime.combine(end_date, dt.time.max, tzinfo=self.start.tzinfo)
        return self.start <= r1 and self.effective_end >= r0
