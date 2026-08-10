from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.presentation.feed_context import build_page_context
from app.presentation.jinja import render_page
from app.settings import COOKIE_MUTED_APPS
from app.storage.db import get_db
from app.user_prefs.cookies import cookie_kwargs, should_persist_muted

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Annotated[Session, Depends(get_db)]):
    raw_cookie = request.cookies.get(COOKIE_MUTED_APPS)
    page = build_page_context(db, request)
    response = render_page(request, "index.html", {"page": page, **page.sidebar.as_template_dict()})
    if should_persist_muted(raw_cookie, page.muted_apps):
        response.set_cookie(
            COOKIE_MUTED_APPS,
            ",".join(page.muted_apps),
            **cookie_kwargs(),
        )
    return response
