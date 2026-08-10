from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.catalog.apps import apps_by_slug, apps_sorted_by_last_update
from app.presentation.view_models import PageContext, build_feed_views
from app.settings import COOKIE_MUTED_APPS, COOKIE_THEME, DEFAULT_THEME, THEMES
from app.storage.entries_repo import (
    count_entries,
    get_last_new_entries_count,
    latest_published_per_app,
    latest_sync,
    list_entries,
    sync_errors_by_slug,
)
from app.user_prefs.cookies import parse_muted_apps, visible_apps_from_muted


def theme_from_cookie(raw: str | None) -> str:
    if raw in THEMES:
        return raw
    return DEFAULT_THEME


def _request_theme_and_muted(request: Request) -> tuple[str, list[str]]:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    theme = theme_from_cookie(request.cookies.get(COOKIE_THEME))
    return theme, muted


def build_sidebar_context(db: Session, request: Request) -> PageContext:
    theme, muted = _request_theme_and_muted(request)
    app_last_updates = latest_published_per_app(db)
    return PageContext(
        apps=list(apps_sorted_by_last_update(app_last_updates)),
        muted_apps=muted,
        entries=[],
        theme=theme,
        last_sync=latest_sync(db),
        last_new_entries_count=get_last_new_entries_count(db),
        app_last_updates=app_last_updates,
        sync_errors=sync_errors_by_slug(db),
        has_sync_data=False,
    )


def build_feed_context(db: Session, request: Request) -> PageContext:
    theme, muted = _request_theme_and_muted(request)
    visible = visible_apps_from_muted(muted)
    return PageContext(
        apps=[],
        muted_apps=muted,
        entries=build_feed_views(list_entries(db, app_slugs=visible), apps_by_slug()),
        theme=theme,
        last_sync=None,
        last_new_entries_count=None,
        app_last_updates={},
        sync_errors={},
        has_sync_data=count_entries(db) > 0,
    )


def build_page_context(db: Session, request: Request) -> PageContext:
    theme, muted = _request_theme_and_muted(request)
    visible = visible_apps_from_muted(muted)
    app_last_updates = latest_published_per_app(db)
    return PageContext(
        apps=list(apps_sorted_by_last_update(app_last_updates)),
        muted_apps=muted,
        entries=build_feed_views(list_entries(db, app_slugs=visible), apps_by_slug()),
        theme=theme,
        last_sync=latest_sync(db),
        last_new_entries_count=get_last_new_entries_count(db),
        app_last_updates=app_last_updates,
        sync_errors=sync_errors_by_slug(db),
        has_sync_data=count_entries(db) > 0,
    )
