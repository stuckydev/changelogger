from __future__ import annotations

from app.catalog.apps import all_slugs

COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def cookie_kwargs(max_age: int = COOKIE_MAX_AGE) -> dict:
    return {
        "max_age": max_age,
        "httponly": False,
        "samesite": "lax",
        "path": "/",
    }


def parse_muted_apps(raw: str | None) -> list[str]:
    if raw is None or not raw.strip():
        return []
    known = set(all_slugs())
    return [part.strip() for part in raw.split(",") if part.strip() in known]


def visible_apps_from_muted(muted: list[str]) -> list[str]:
    muted_set = set(muted)
    return [slug for slug in all_slugs() if slug not in muted_set]


def should_persist_muted(raw: str | None, muted: list[str]) -> bool:
    if raw is None:
        return bool(muted)
    stored = [part.strip() for part in raw.split(",") if part.strip()]
    return stored != muted
