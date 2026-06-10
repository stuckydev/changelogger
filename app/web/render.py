from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import AppConfig
from app.core.constants import APP_PREFIX, ROOT_DIR
from app.core.date_utils import format_sync_time, update_freshness
from app.domain.changelog import highlights_from_json
from app.web.highlight import highlight_mtg_terms

TEMPLATES_DIR = ROOT_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def static_asset_version() -> str:
    css_path = ROOT_DIR / "app" / "static" / "app.css"
    if css_path.exists():
        return str(int(css_path.stat().st_mtime))
    return "1"


@dataclass
class FeedEntryView:
    id: str
    app_slug: str
    app_name: str
    app_logo_src: str
    title: str
    summary: str
    highlights: list[str]
    source_url: str
    published_at: datetime
    published_label: str


@dataclass
class PageContext:
    apps: list[AppConfig]
    muted_apps: list[str]
    entries: list[FeedEntryView]
    theme: str
    last_sync: datetime | None
    app_last_updates: dict[str, datetime]
    has_sync_data: bool = False


GERMAN_MONTHS = (
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def format_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def format_month_year(value: datetime) -> str:
    return f"{GERMAN_MONTHS[value.month]} {value.year}"


def month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


templates.env.filters["month_year"] = format_month_year
templates.env.filters["month_key"] = month_key
templates.env.filters["format_date"] = format_date
templates.env.filters["sync_time"] = format_sync_time
templates.env.filters["update_freshness"] = update_freshness
templates.env.filters["mtg_terms"] = highlight_mtg_terms


def build_feed_views(entries, apps_by_slug: dict[str, AppConfig]) -> list[FeedEntryView]:
    views: list[FeedEntryView] = []
    for entry in entries:
        app = apps_by_slug.get(entry.app_slug)
        if not app:
            continue
        highlights = highlights_from_json(entry.highlights)
        views.append(
            FeedEntryView(
                id=entry.id,
                app_slug=entry.app_slug,
                app_name=app.display_name,
                app_logo_src=app.logo_src,
                title=entry.title,
                summary=entry.summary,
                highlights=highlights,
                source_url=entry.source_url,
                published_at=entry.published_at,
                published_label=format_date(entry.published_at),
            )
        )
    return views


def render_page(request, template_name: str, context: dict):
    context.setdefault("app_prefix", APP_PREFIX)
    context.setdefault("static_asset_version", static_asset_version())
    return templates.TemplateResponse(request, template_name, context)
