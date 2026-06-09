from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import all_slugs, apps_by_slug
from app.constants import COOKIE_MUTED_APPS, COOKIE_THEME
from app.cookies import cookie_kwargs
from app.crud import count_entries, latest_sync, list_entries
from app.db import get_db
from app.routers.render import build_feed_views, render_page
from app.selection import parse_muted_apps, visible_apps_from_muted

router = APIRouter(prefix="/api")


class PreferencesPayload(BaseModel):
    muted_apps: list[str] = Field(default_factory=list)
    theme: str | None = None


@router.get("/feed", response_class=HTMLResponse)
def feed_partial(request: Request, db: Annotated[Session, Depends(get_db)]):
    muted = parse_muted_apps(request.cookies.get(COOKIE_MUTED_APPS))
    visible = visible_apps_from_muted(muted)
    has_sync_data = count_entries(db) > 0
    entries = list_entries(db, app_slugs=visible)

    return render_page(
        request,
        "partials/feed.html",
        {
            "entries": build_feed_views(entries, apps_by_slug()),
            "has_sync_data": has_sync_data,
        },
    )


@router.post("/preferences")
def save_preferences(payload: PreferencesPayload):
    known = set(all_slugs())
    muted = [slug for slug in payload.muted_apps if slug in known]

    response = JSONResponse({"ok": True, "muted_apps": muted, "theme": payload.theme})
    response.set_cookie(
        COOKIE_MUTED_APPS,
        ",".join(muted),
        **cookie_kwargs(),
    )
    if payload.theme in {"light", "dark"}:
        response.set_cookie(COOKIE_THEME, payload.theme, **cookie_kwargs())

    return response


@router.get("/status")
def status(request: Request, db: Annotated[Session, Depends(get_db)]):
    last_sync = latest_sync(db)
    return {
        "last_sync": last_sync.isoformat() if last_sync else None,
        "sync_errors": getattr(request.app.state, "sync_errors", {}),
        "entry_count": count_entries(db),
    }
