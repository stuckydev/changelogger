from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.catalog.apps import AppConfig
from app.models.changelog import derive_summary, highlights_from_json


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
    sync_errors: dict[str, str]
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


def format_sidebar_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.year < datetime.now().year:
        return value.strftime("%d.%m.%Y")
    return value.strftime("%d.%m.")


def format_month_year(value: datetime) -> str:
    return f"{GERMAN_MONTHS[value.month]} {value.year}"


def month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


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
                summary=derive_summary(highlights, title=entry.title),
                highlights=highlights,
                source_url=entry.source_url,
                published_at=entry.published_at,
                published_label=format_date(entry.published_at),
            )
        )
    return views
