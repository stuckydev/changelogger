from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.catalog.apps import apps_by_slug, apps_sorted_by_last_update
from app.presentation.view_models import PageContext, build_feed_views
from app.settings import COOKIE_MUTED_APPS, COOKIE_THEME, DEFAULT_THEME
from app.storage.entries_repo import count_entries, latest_published_per_app, latest_sync, list_entries
from app.storage.sync_metadata_repo import get_last_new_entries_count
from app.storage.sync_status_repo import sync_errors_by_slug
from app.user_prefs.cookies import parse_muted_apps, visible_apps_from_muted


def theme_from_cookie(raw: str | None) -> str:
    if raw in {"light", "dark"}:
        return raw
    return DEFAULT_THEME


def build_page_context(db: Session, request: Request) -> PageContext:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    visible = visible_apps_from_muted(muted)
    app_last_updates = latest_published_per_app(db)

    return PageContext(
        apps=list(apps_sorted_by_last_update(app_last_updates)),
        muted_apps=muted,
        entries=build_feed_views(list_entries(db, app_slugs=visible), apps_by_slug()),
        theme=theme_from_cookie(request.cookies.get(COOKIE_THEME)),
        last_sync=latest_sync(db),
        last_new_entries_count=get_last_new_entries_count(db),
        app_last_updates=app_last_updates,
        sync_errors=sync_errors_by_slug(db),
        has_sync_data=count_entries(db) > 0,
    )


def feed_template_context(page: PageContext) -> dict:
    return {
        "entries": page.entries,
        "has_sync_data": page.has_sync_data,
    }


def sidebar_template_context(page: PageContext) -> dict:
    return {
        "apps": page.apps,
        "muted_apps": page.muted_apps,
        "app_last_updates": page.app_last_updates,
        "sync_errors": page.sync_errors,
        "last_sync": page.last_sync,
        "last_new_entries_count": page.last_new_entries_count,
    }
