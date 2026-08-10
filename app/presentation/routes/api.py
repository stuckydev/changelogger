from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.catalog.apps import all_slugs
from app.presentation.feed_context import build_feed_context, build_sidebar_context
from app.presentation.jinja import render_page, render_template
from app.settings import COOKIE_MUTED_APPS, COOKIE_THEME, THEMES
from app.storage.db import get_db
from app.user_prefs.cookies import cookie_kwargs

router = APIRouter(prefix="/api")


class PreferencesPayload(BaseModel):
    muted_apps: list[str] = Field(default_factory=list)
    theme: str | None = None


@router.get("/feed", response_class=HTMLResponse)
def feed_partial(request: Request, db: Annotated[Session, Depends(get_db)]):
    return render_page(
        request,
        "partials/feed.html",
        build_feed_context(db, request).as_template_dict(),
    )


@router.get("/sidebar")
def sidebar_partial(request: Request, db: Annotated[Session, Depends(get_db)]):
    ctx = build_sidebar_context(db, request).as_template_dict()
    return JSONResponse(
        {
            "apps_html": render_template("partials/sidebar_apps.html", ctx),
            "sync_html": render_template("partials/sidebar_sync.html", ctx),
        }
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
    if payload.theme in THEMES:
        response.set_cookie(COOKIE_THEME, payload.theme, **cookie_kwargs())

    return response
