import datetime as dt
from app.utils.dates import parse_ddmmyyyy, SprintWindow

def test_parse_ddmmyyyy_ok():
    assert parse_ddmmyyyy("07012026", "date") == dt.date(2026, 1, 7)

def test_contains_date():
    start = dt.datetime(2026,1,1,0,0,0, tzinfo=dt.timezone.utc)
    end = dt.datetime(2026,1,14,0,0,0, tzinfo=dt.timezone.utc)
    w = SprintWindow(start=start, end=end, complete=None)
    assert w.contains_date(dt.date(2026,1,7)) is True
    assert w.contains_date(dt.date(2026,2,1)) is False

def test_overlap_range():
    start = dt.datetime(2026,1,1,0,0,0, tzinfo=dt.timezone.utc)
    end = dt.datetime(2026,1,14,0,0,0, tzinfo=dt.timezone.utc)
    w = SprintWindow(start=start, end=end, complete=None)
    assert w.overlaps_range(dt.date(2026,1,10), dt.date(2026,1,20)) is True
    assert w.overlaps_range(dt.date(2026,2,1), dt.date(2026,2,2)) is False
