from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

DISPLAY_TZ = ZoneInfo("Europe/Zurich")

# WinUtil-style tags: 26.05.12 → 2026-05-12
DOT_VERSION_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{2})\b")


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


def date_from_dot_version(title: str) -> datetime | None:
    match = DOT_VERSION_RE.search(title)
    if not match:
        return None
    year = 2000 + int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def utc_naive_to_display(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc).astimezone(DISPLAY_TZ)


def format_sync_time(value: datetime) -> str:
    return utc_naive_to_display(value).strftime("%d.%m.%Y %H:%M")


def update_freshness(value: datetime | None) -> str:
    """Return a CSS modifier for how recent an app's last update is."""
    if value is None:
        return ""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    age = now - value
    if age <= timedelta(days=30):
        return "fresh"
    if age <= timedelta(days=180):
        return "aging"
    return "stale"
