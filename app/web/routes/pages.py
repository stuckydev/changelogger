from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import apps_by_slug, apps_sorted_by_last_update
from app.core.constants import COOKIE_MUTED_APPS, COOKIE_THEME, DEFAULT_THEME
from app.core.db import get_db
from app.domain.preferences import cookie_kwargs, parse_muted_apps, should_persist_muted, visible_apps_from_muted
from app.repositories.entries import count_entries, latest_published_per_app, latest_sync, list_entries
from app.web.render import PageContext, build_feed_views, render_page

router = APIRouter()


def _theme_from_cookie(raw: str | None) -> str:
    if raw in {"light", "dark"}:
        return raw
    return DEFAULT_THEME


def _build_context(db: Session, request: Request) -> PageContext:
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    visible = visible_apps_from_muted(muted)
    has_sync_data = count_entries(db) > 0
    entries = list_entries(db, app_slugs=visible)
    app_last_updates = latest_published_per_app(db)
    apps = list(apps_sorted_by_last_update(app_last_updates))

    return PageContext(
        apps=apps,
        muted_apps=muted,
        entries=build_feed_views(entries, apps_by_slug()),
        theme=_theme_from_cookie(request.cookies.get(COOKIE_THEME)),
        last_sync=latest_sync(db),
        app_last_updates=app_last_updates,
        has_sync_data=has_sync_data,
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    raw_cookie = request.cookies.get(COOKIE_MUTED_APPS)
    ctx = _build_context(db, request)
    response = render_page(request, "index.html", {"page": ctx})
    if should_persist_muted(raw_cookie, ctx.muted_apps):
        response.set_cookie(
            COOKIE_MUTED_APPS,
            ",".join(ctx.muted_apps),
            **cookie_kwargs(),
        )
    return response
