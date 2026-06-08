from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import AppConfig
from app.constants import APP_PREFIX, ROOT_DIR
from app.date_utils import format_sync_time
from app.highlight import highlight_mtg_terms
from app.services.parsers.base import highlights_from_json

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
    categories: list[str]
    source_url: str
    published_at: datetime
    published_label: str


@dataclass
class PageContext:
    apps: list[AppConfig]
    selected_apps: list[str]
    read_entries: set[str]
    entries: list[FeedEntryView]
    theme: str
    last_sync: datetime | None
    sync_errors: dict[str, str]
    is_loading: bool = False


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
templates.env.filters["sync_time"] = format_sync_time
templates.env.filters["mtg_terms"] = highlight_mtg_terms


def display_categories(categories: list[str]) -> list[str]:
    labels: list[str] = []
    for category in categories:
        label = "Fix" if category == "Fix" else "Update"
        if label not in labels:
            labels.append(label)
    return labels or ["Update"]


def build_feed_views(entries, apps_by_slug: dict[str, AppConfig]) -> list[FeedEntryView]:
    views: list[FeedEntryView] = []
    for entry in entries:
        app = apps_by_slug.get(entry.app_slug)
        if not app:
            continue
        raw_categories = [part for part in entry.categories.split(",") if part]
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
                categories=display_categories(raw_categories),
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
