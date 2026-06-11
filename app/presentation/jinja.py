from __future__ import annotations

import re

from fastapi.templating import Jinja2Templates

from app.settings import APP_PREFIX, STATIC_DIR, TEMPLATES_DIR
from app.utils.date_utils import format_sync_time, update_freshness
from app.presentation.highlight import highlight_mtg_terms
from app.presentation.view_models import (
    days_since,
    format_date,
    format_month_year,
    format_relative_date,
    format_sidebar_date,
    month_key,
)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_css_inline_cache: tuple[str, str] | None = None


def _minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>~])\s*", r"\1", css)
    return css.strip()


def static_asset_version() -> str:
    css_path = STATIC_DIR / "app.css"
    if css_path.exists():
        return str(int(css_path.stat().st_mtime))
    return "1"


def inline_app_styles() -> str:
    global _css_inline_cache
    css_path = STATIC_DIR / "app.css"
    if not css_path.exists():
        return ""
    version = static_asset_version()
    if _css_inline_cache and _css_inline_cache[0] == version:
        return _css_inline_cache[1]
    css = _minify_css(css_path.read_text(encoding="utf-8"))
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
templates.env.filters["mtg_terms"] = highlight_mtg_terms


def render_page(request, template_name: str, context: dict):
    context.setdefault("app_prefix", APP_PREFIX)
    context.setdefault("static_asset_version", static_asset_version())
    context.setdefault("inline_app_styles", inline_app_styles())
    return templates.TemplateResponse(request, template_name, context)


def render_template(template_name: str, context: dict) -> str:
    context.setdefault("app_prefix", APP_PREFIX)
    context.setdefault("static_asset_version", static_asset_version())
    return templates.get_template(template_name).render(context)
