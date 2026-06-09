from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import apps_by_slug, apps_sorted_by_last_update
from app.constants import COOKIE_MUTED_APPS, COOKIE_SELECTED_APPS, COOKIE_THEME, DEFAULT_THEME
from app.cookies import cookie_kwargs
from app.crud import count_entries, latest_published_per_app, latest_sync, list_entries
from app.db import get_db
from app.routers.render import PageContext, build_feed_views, render_page
from app.selection import (
    muted_from_legacy_selected,
    parse_muted_apps,
    should_persist_muted,
    visible_apps_from_muted,
)

router = APIRouter()


def _theme_from_cookie(raw: str | None) -> str:
    if raw in {"light", "dark"}:
        return raw
    return DEFAULT_THEME


def _muted_apps_from_request(request: Request) -> list[str]:
    raw_muted = request.cookies.get(COOKIE_MUTED_APPS)
    if raw_muted is not None:
        return parse_muted_apps(raw_muted)
    return muted_from_legacy_selected(request.cookies.get(COOKIE_SELECTED_APPS))


def _build_context(db: Session, request: Request, *, is_loading: bool = False) -> PageContext:
    muted = _muted_apps_from_request(request)
    visible = visible_apps_from_muted(muted)
    has_sync_data = count_entries(db) > 0
    entries = list_entries(db, app_slugs=visible)
    sync_errors = getattr(request.app.state, "sync_errors", {})
    app_last_updates = latest_published_per_app(db)
    apps = list(apps_sorted_by_last_update(app_last_updates))

    return PageContext(
        apps=apps,
        muted_apps=muted,
        entries=build_feed_views(entries, apps_by_slug()),
        theme=_theme_from_cookie(request.cookies.get(COOKIE_THEME)),
        last_sync=latest_sync(db),
        app_last_updates=app_last_updates,
        sync_errors=sync_errors,
        has_sync_data=has_sync_data,
        is_loading=is_loading,
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    raw_cookie = request.cookies.get(COOKIE_MUTED_APPS)
    ctx = _build_context(db, request)
    response = render_page(
        request,
        "index.html",
        {
            "page": ctx,
            "apps_json": json.dumps(
                [
                    {
                        "slug": app.slug,
                        "name": app.display_name,
                        "color": app.color,
                        "logo": app.logo_src,
                    }
                    for app in ctx.apps
                ]
            ),
        },
    )
    if should_persist_muted(raw_cookie, ctx.muted_apps):
        response.set_cookie(
            COOKIE_MUTED_APPS,
            ",".join(ctx.muted_apps),
            **cookie_kwargs(),
        )
    return response


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]):
    from sqlalchemy import text

    db.execute(text("SELECT 1"))
    return {"status": "ok"}
