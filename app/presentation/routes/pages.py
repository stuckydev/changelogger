from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.settings import COOKIE_MUTED_APPS
from app.storage.db import get_db
from app.user_prefs.cookies import cookie_kwargs, should_persist_muted
from app.presentation.feed_context import build_page_context, build_sidebar_context
from app.presentation.jinja import render_page

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    raw_cookie = request.cookies.get(COOKIE_MUTED_APPS)
    ctx = build_page_context(db, request)
    sidebar_ctx = build_sidebar_context(db, request)
    response = render_page(request, "index.html", {"page": ctx, **sidebar_ctx})
    if should_persist_muted(raw_cookie, ctx.muted_apps):
        response.set_cookie(
            COOKIE_MUTED_APPS,
            ",".join(ctx.muted_apps),
            **cookie_kwargs(),
        )
    return response
