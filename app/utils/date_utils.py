from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

DISPLAY_TZ = ZoneInfo("Europe/Zurich")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except (TypeError, ValueError, IndexError):
        pass

    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def parse_datetime_or_now(value: str | None) -> datetime:
    return parse_datetime(value) or datetime.now(timezone.utc).replace(tzinfo=None)


def utc_naive_to_display(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc).astimezone(DISPLAY_TZ)


def format_sync_time(value: datetime) -> str:
    return utc_naive_to_display(value).strftime("%d.%m.%Y %H:%M")


def seconds_until_next_hour() -> float:
    now = datetime.now(DISPLAY_TZ)
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return (next_hour - now).total_seconds()
