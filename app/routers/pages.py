from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config import load_apps
from app.constants import COOKIE_SELECTED_APPS, COOKIE_THEME, DEFAULT_THEME
from app.crud import latest_sync, list_entries
from app.db import get_db
from app.routers.render import PageContext, build_feed_views, render_page
from app.selection import parse_selected_apps, should_persist_selection

router = APIRouter()


def _cookie_kwargs(max_age: int = 60 * 60 * 24 * 365) -> dict:
    return {
        "max_age": max_age,
        "httponly": False,
        "samesite": "lax",
        "path": "/",
    }


def _theme_from_cookie(raw: str | None) -> str:
    if raw in {"light", "dark"}:
        return raw
    return DEFAULT_THEME


def _build_context(db: Session, request: Request, *, is_loading: bool = False) -> PageContext:
    apps = list(load_apps())
    apps_by_slug = {app.slug: app for app in apps}
    selected = parse_selected_apps(request.cookies.get(COOKIE_SELECTED_APPS))
    entries = list_entries(db)
    sync_errors = request.app.state.sync_errors if hasattr(request.app.state, "sync_errors") else {}

    return PageContext(
        apps=apps,
        selected_apps=selected,
        entries=build_feed_views(entries, apps_by_slug),
        theme=_theme_from_cookie(request.cookies.get(COOKIE_THEME)),
        last_sync=latest_sync(db),
        sync_errors=sync_errors,
        is_loading=is_loading,
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    raw_cookie = request.cookies.get(COOKIE_SELECTED_APPS)
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
    if should_persist_selection(raw_cookie, ctx.selected_apps):
        response.set_cookie(
            COOKIE_SELECTED_APPS,
            ",".join(ctx.selected_apps),
            **_cookie_kwargs(),
        )
    return response


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]):
    from sqlalchemy import text

    db.execute(text("SELECT 1"))
    return {"status": "ok"}
