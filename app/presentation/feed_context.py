from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.catalog.apps import apps_by_slug, apps_sorted_by_last_update
from app.settings import COOKIE_MUTED_APPS, COOKIE_THEME, DEFAULT_THEME
from app.user_prefs.cookies import parse_muted_apps, visible_apps_from_muted
from app.presentation.view_models import PageContext, build_feed_views
from app.storage.entries_repo import count_entries, latest_published_per_app, latest_sync, list_entries
from app.storage.sync_metadata_repo import get_last_new_entries_count
from app.storage.sync_status_repo import sync_errors_by_slug


def theme_from_cookie(raw: str | None) -> str:
    if raw in {"light", "dark"}:
        return raw
    return DEFAULT_THEME


def build_page_context(db: Session, request: Request) -> PageContext:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    visible = visible_apps_from_muted(muted)
    has_sync_data = count_entries(db) > 0
    entries = list_entries(db, app_slugs=visible)
    app_last_updates = latest_published_per_app(db)

    return PageContext(
        apps=list(apps_sorted_by_last_update(app_last_updates)),
        muted_apps=muted,
        entries=build_feed_views(entries, apps_by_slug()),
        theme=theme_from_cookie(request.cookies.get(COOKIE_THEME)),
        last_sync=latest_sync(db),
        last_new_entries_count=get_last_new_entries_count(db),
        app_last_updates=app_last_updates,
        sync_errors=sync_errors_by_slug(db),
        has_sync_data=has_sync_data,
    )


def build_feed_context(db: Session, request: Request) -> dict:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    visible = visible_apps_from_muted(muted)
    has_sync_data = count_entries(db) > 0
    entries = list_entries(db, app_slugs=visible)

    return {
        "entries": build_feed_views(entries, apps_by_slug()),
        "has_sync_data": has_sync_data,
    }


def build_sidebar_context(db: Session, request: Request) -> dict:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    app_last_updates = latest_published_per_app(db)

    return {
        "apps": list(apps_sorted_by_last_update(app_last_updates)),
        "muted_apps": muted,
        "app_last_updates": app_last_updates,
        "sync_errors": sync_errors_by_slug(db),
        "last_sync": latest_sync(db),
        "last_new_entries_count": get_last_new_entries_count(db),
    }
