from __future__ import annotations

from datetime import datetime

from app.core.config import AppConfig
from app.core.constants import HIGHLIGHT_LIMIT, ZENDESK_HIGHLIGHT_LIMIT
from app.core.date_utils import parse_datetime
from app.domain.changelog import ParsedEntry, finalize_entry, pick_recent
from app.infra.http import get_http_client
from app.parsers.capacities_html import parse_capacities_html
from app.parsers.cursor_html import parse_cursor_html
from app.parsers.github_releases import (
    apply_github_release_dates,
    parse_github_releases,
    parse_github_releases_simple,
)
from app.parsers.microsoft_store_html import parse_microsoft_store_html
from app.parsers.notion_html import parse_notion_html
from app.parsers.rss import parse_rss
from app.parsers.todoist_html import parse_todoist_html
from app.parsers.zendesk_articles import parse_zendesk_articles


class FetchError(Exception):
    def __init__(self, app_slug: str, message: str) -> None:
        self.app_slug = app_slug
        super().__init__(message)


async def fetch_source(app: AppConfig) -> str:
    client = await get_http_client()
    response = await client.get(app.source_url)
    if response.status_code >= 400:
        raise FetchError(app.slug, f"HTTP {response.status_code} for {app.source_url}")
    return response.text


async def fetch_github_release_dates(github_repo: str) -> dict[str, datetime]:
    client = await get_http_client()
    response = await client.get(
        f"https://api.github.com/repos/{github_repo}/releases",
        params={"per_page": 30},
        headers={"Accept": "application/vnd.github+json"},
    )
    if response.status_code >= 400:
        return {}

    from app.parsers.github_releases import tag_lookup_keys

    dates: dict[str, datetime] = {}
    for release in response.json():
        tag_name = (release.get("tag_name") or "").strip()
        published = parse_datetime(release.get("published_at"))
        if not tag_name or published is None:
            continue
        for key in tag_lookup_keys(tag_name):
            dates[key] = published
    return dates


async def parse_recent(app: AppConfig, content: str) -> list[ParsedEntry]:
    entries: list[ParsedEntry]
    if app.parser == "rss":
        entries = parse_rss(content)
    elif app.parser == "todoist_html":
        entries = parse_todoist_html(content, source_url=app.source_url)
    elif app.parser == "notion_html":
        entries = parse_notion_html(content, source_url=app.source_url)
    elif app.parser == "github_releases":
        if app.github_simple:
            entries = parse_github_releases_simple(content)
        else:
            entries = parse_github_releases(content)
    elif app.parser == "capacities_html":
        entries = parse_capacities_html(content, source_url=app.source_url)
    elif app.parser == "cursor_html":
        entries = parse_cursor_html(content, source_url=app.source_url)
    elif app.parser == "microsoft_store_html":
        entries = parse_microsoft_store_html(content, source_url=app.source_url)
    elif app.parser == "zendesk_articles":
        entries = parse_zendesk_articles(content, source_url=app.source_url)
    else:
        raise FetchError(app.slug, f"Unknown parser: {app.parser}")

    if app.parser == "github_releases" and app.github_repo:
        release_dates = await fetch_github_release_dates(app.github_repo)
        entries = apply_github_release_dates(entries, release_dates)

    highlight_limit = ZENDESK_HIGHLIGHT_LIMIT if app.parser == "zendesk_articles" else HIGHLIGHT_LIMIT
    entries = [finalize_entry(entry, highlight_limit=highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries
