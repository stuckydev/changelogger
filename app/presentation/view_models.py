from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from markupsafe import Markup, escape

from app.catalog.apps import AppConfig
from app.models.changelog import highlights_from_json
from app.presentation.highlight import highlight_terms


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

    def as_template_dict(self) -> dict:
        return {
            "entries": self.entries,
            "has_sync_data": self.has_sync_data,
        }


@dataclass
class SidebarContext:
    apps: list[AppConfig]
    muted_apps: list[str]
    theme: str
    last_sync: datetime | None
    app_last_updates: dict[str, datetime]
    sync_errors: dict[str, str]
    last_new_entries_count: int | None

    def as_template_dict(self) -> dict:
        return {
            "apps": self.apps,
            "muted_apps": self.muted_apps,
            "app_last_updates": self.app_last_updates,
            "sync_errors": self.sync_errors,
            "last_sync": self.last_sync,
            "last_new_entries_count": self.last_new_entries_count,
        }


@dataclass
class PageContext:
    feed: FeedContext
    sidebar: SidebarContext

    @property
    def theme(self) -> str:
        return self.sidebar.theme

    @property
    def muted_apps(self) -> list[str]:
        return self.sidebar.muted_apps

    @property
    def entries(self) -> list[FeedEntryView]:
        return self.feed.entries

    @property
    def has_sync_data(self) -> bool:
        return self.feed.has_sync_data


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


def days_since(value: datetime) -> int:
    return (datetime.now().date() - value.date()).days


def format_relative_date(value: datetime) -> str:
    delta = days_since(value)
    if delta <= 0:
        return "heute"
    if delta == 1:
        return "gestern"
    if delta < 7:
        return f"vor {delta} Tagen"
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


def update_freshness(value: datetime | None) -> str:
    """Return a CSS modifier for how recent an app's last update is."""
    if value is None:
        return ""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    age = now - value
    if age <= timedelta(days=30):
        return "fresh"
    if age <= timedelta(days=180):
        return "aging"
    return "stale"


def _display_text(app: AppConfig, text: str) -> Markup:
    if app.highlight_terms:
        return highlight_terms(text, app.highlight_terms)
    return Markup(escape(text))


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
                title_html=_display_text(app, entry.title),
                highlights=highlights,
                highlights_html=[_display_text(app, item) for item in highlights],
                source_url=entry.source_url,
                published_at=entry.published_at,
                published_label=format_date(entry.published_at),
            )
        )
    return views
