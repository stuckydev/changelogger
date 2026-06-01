from __future__ import annotations

from app.config import all_slugs


def parse_selected_apps(raw: str | None) -> list[str]:
    """Default: all apps selected. Cookie stores explicit user choices."""
    known = all_slugs()
    if not raw or not raw.strip():
        return known

    known_set = set(known)
    selected = [part.strip() for part in raw.split(",") if part.strip() in known_set]
    if not selected:
        return known

    # Auto-enable apps newly added to config/apps.yaml
    selected_set = set(selected)
    for slug in known:
        if slug not in selected_set:
            selected.append(slug)

    return selected


def should_persist_selection(raw: str | None, selected: list[str]) -> bool:
    if not raw or not raw.strip():
        return True
    stored = [part.strip() for part in raw.split(",") if part.strip()]
    return stored != selected
