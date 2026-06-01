from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import all_slugs, load_apps
from app.constants import COOKIE_SELECTED_APPS, COOKIE_THEME
from app.crud import list_entries
from app.db import get_db
from app.routers.render import build_feed_views, render_page
from app.selection import parse_selected_apps

router = APIRouter(prefix="/api")


class PreferencesPayload(BaseModel):
    selected_apps: list[str] = Field(default_factory=list)
    theme: str | None = None


def _cookie_kwargs(max_age: int = 60 * 60 * 24 * 365) -> dict:
    return {
        "max_age": max_age,
        "httponly": False,
        "samesite": "lax",
        "path": "/",
    }


@router.get("/feed", response_class=HTMLResponse)
def feed_partial(request: Request, db: Annotated[Session, Depends(get_db)]):
    selected = parse_selected_apps(request.cookies.get(COOKIE_SELECTED_APPS))
    apps_by_slug = {app.slug: app for app in load_apps()}
    entries = list_entries(db)

    return render_page(
        request,
        "partials/feed.html",
        {
            "entries": build_feed_views(entries, apps_by_slug),
            "selected_apps": selected,
            "sync_errors": getattr(request.app.state, "sync_errors", {}),
        },
    )


@router.post("/preferences")
def save_preferences(payload: PreferencesPayload, response: Response):
    known = set(all_slugs())
    selected = [slug for slug in payload.selected_apps if slug in known]
    if not selected:
        selected = all_slugs()

    response.set_cookie(
        COOKIE_SELECTED_APPS,
        ",".join(selected),
        **_cookie_kwargs(),
    )
    if payload.theme in {"light", "dark"}:
        response.set_cookie(COOKIE_THEME, payload.theme, **_cookie_kwargs())

    return JSONResponse({"ok": True, "selected_apps": selected, "theme": payload.theme})


@router.get("/status")
def status(request: Request, db: Annotated[Session, Depends(get_db)]):
    from app.crud import latest_sync

    return {
        "last_sync": latest_sync(db).isoformat() if latest_sync(db) else None,
        "sync_errors": getattr(request.app.state, "sync_errors", {}),
        "entry_count": len(list_entries(db, limit=1000)),
    }
