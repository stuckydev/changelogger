from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from markupsafe import Markup

from app.catalog.apps import AppConfig
from app.models.changelog import StoredEntry
from app.presentation.highlight import highlight_terms
from app.utils.date_utils import now_display, now_utc_naive, utc_naive_to_display


@dataclass
class FeedEntryView:
    id: str
    app_slug: str
    app_name: str
    app_logo_src: str
    title: str
    title_html: Markup
    highlights: list[str]
    highlights_html: list[Markup]
    source_url: str
    published_at: datetime
    published_label: str


@dataclass
class FeedContext:
    entries: list[FeedEntryView]
    has_sync_data: bool


@dataclass
class SidebarContext:
    apps: list[AppConfig]
    muted_apps: list[str]
    theme: str
    last_sync: datetime | None
    app_last_updates: dict[str, datetime]
    sync_errors: dict[str, str]
    last_new_entries_count: int | None


@dataclass
class PageContext:
    feed: FeedContext
    sidebar: SidebarContext


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
    return utc_naive_to_display(value).strftime("%d.%m.%Y")


def days_since(value: datetime) -> int:
    published = utc_naive_to_display(value).date()
    return (now_display().date() - published).days


def format_relative_date(value: datetime) -> str:
    delta = days_since(value)
    if delta <= 0:
        return "heute"
    if delta == 1:
        return "gestern"
    if delta < 7:
        return f"vor {delta} Tagen"
    return format_date(value)


def format_sidebar_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    display = utc_naive_to_display(value)
    if display.year < now_display().year:
        return display.strftime("%d.%m.%Y")
    return display.strftime("%d.%m.")


def format_month_year(value: datetime) -> str:
    display = utc_naive_to_display(value)
    return f"{GERMAN_MONTHS[display.month]} {display.year}"


def month_key(value: datetime) -> str:
    return utc_naive_to_display(value).strftime("%Y-%m")


def update_freshness(value: datetime | None) -> str:
    if value is None:
        return ""
    age = now_utc_naive() - value
    if age <= timedelta(days=30):
        return "fresh"
    if age <= timedelta(days=180):
        return "aging"
    return "stale"


def cap_entries_per_app(
    entries: list[StoredEntry], apps_by_slug: dict[str, AppConfig]
) -> list[StoredEntry]:
    """Keep each app's newest entries. `entries` must already be newest-first."""
    kept: list[StoredEntry] = []
    seen: dict[str, int] = {}
    for entry in entries:
        app = apps_by_slug.get(entry.app_slug)
        if app is None:
            continue
        count = seen.get(entry.app_slug, 0)
        if count >= app.entries_limit:
            continue
        seen[entry.app_slug] = count + 1
        kept.append(entry)
    return kept


def build_feed_views(
    entries: list[StoredEntry], apps_by_slug: dict[str, AppConfig]
) -> list[FeedEntryView]:
    views: list[FeedEntryView] = []
    for entry in entries:
        app = apps_by_slug.get(entry.app_slug)
        if not app:
            continue
        views.append(
            FeedEntryView(
                id=entry.id,
                app_slug=entry.app_slug,
                app_name=app.display_name,
                app_logo_src=app.logo_src,
                title=entry.title,
                title_html=highlight_terms(entry.title, app.highlight_terms),
                highlights=entry.highlights,
                highlights_html=[
                    highlight_terms(item, app.highlight_terms) for item in entry.highlights
                ],
                source_url=entry.source_url,
                published_at=entry.published_at,
                published_label=format_date(entry.published_at),
            )
        )
    return views
