from __future__ import annotations

from app.config import all_slugs


def parse_muted_apps(raw: str | None) -> list[str]:
    """Default: no apps muted when cookie is missing or empty."""
    known = all_slugs()
    if raw is None or not raw.strip():
        return []

    known_set = set(known)
    return [part.strip() for part in raw.split(",") if part.strip() in known_set]


def visible_apps_from_muted(muted: list[str]) -> list[str]:
    muted_set = set(muted)
    return [slug for slug in all_slugs() if slug not in muted_set]


def muted_from_legacy_selected(raw: str | None) -> list[str]:
    """Convert a legacy selected-apps cookie into a muted-apps list."""
    known = all_slugs()
    if raw is None:
        return []
    if not raw.strip():
        return known

    known_set = set(known)
    selected = {part.strip() for part in raw.split(",") if part.strip() in known_set}
    return [slug for slug in known if slug not in selected]


def should_persist_muted(raw: str | None, muted: list[str]) -> bool:
    if raw is None:
        return bool(muted)
    stored = [part.strip() for part in raw.split(",") if part.strip()]
    return stored != muted
