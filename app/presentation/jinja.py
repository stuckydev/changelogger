from __future__ import annotations

import re
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.settings import APP_PREFIX, STATIC_DIR, TEMPLATES_DIR
from app.utils.date_utils import format_sync_time, update_freshness
from app.presentation.view_models import (
    days_since,
    format_date,
    format_month_year,
    format_relative_date,
    format_sidebar_date,
    month_key,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_CSS_FILES = ("tokens.css", "shell.css", "feed.css")
_css_inline_cache: tuple[str, str] | None = None


def _minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>~])\s*", r"\1", css)
    return css.strip()


def _css_paths() -> list[Path]:
    return [STATIC_DIR / name for name in _CSS_FILES]


def static_asset_version() -> str:
    mtimes = [path.stat().st_mtime for path in _css_paths() if path.exists()]
    if not mtimes:
        return "1"
    return str(int(max(mtimes)))


def inline_app_styles() -> str:
    global _css_inline_cache
    version = static_asset_version()
    if _css_inline_cache and _css_inline_cache[0] == version:
        return _css_inline_cache[1]
    parts = [path.read_text(encoding="utf-8") for path in _css_paths() if path.exists()]
    css = _minify_css("\n".join(parts))
    _css_inline_cache = (version, css)
    return css


templates.env.filters["month_year"] = format_month_year
templates.env.filters["month_key"] = month_key
templates.env.filters["format_date"] = format_date
templates.env.filters["format_sidebar_date"] = format_sidebar_date
templates.env.filters["relative_date"] = format_relative_date
templates.env.filters["days_since"] = days_since
templates.env.filters["sync_time"] = format_sync_time
templates.env.filters["update_freshness"] = update_freshness


def render_page(request, template_name: str, context: dict):
    context.setdefault("app_prefix", APP_PREFIX)
    context.setdefault("static_asset_version", static_asset_version())
    context.setdefault("inline_app_styles", inline_app_styles())
    return templates.TemplateResponse(request, template_name, context)


def render_template(template_name: str, context: dict) -> str:
    context.setdefault("app_prefix", APP_PREFIX)
    context.setdefault("static_asset_version", static_asset_version())
    return templates.get_template(template_name).render(context)
