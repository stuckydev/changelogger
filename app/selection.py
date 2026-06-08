from __future__ import annotations

from app.config import all_slugs


def parse_selected_apps(raw: str | None) -> list[str]:
    """Default: all apps selected when no cookie. Empty cookie = none selected."""
    known = all_slugs()
    if raw is None:
        return known
    if not raw.strip():
        return []

    known_set = set(known)
    selected = [part.strip() for part in raw.split(",") if part.strip() in known_set]
    if not selected:
        return []

    selected_set = set(selected)
    for slug in known:
        if slug not in selected_set:
            selected.append(slug)

    return selected


def should_persist_selection(raw: str | None, selected: list[str]) -> bool:
    if raw is None:
        return True
    stored = [part.strip() for part in raw.split(",") if part.strip()]
    return stored != selected
