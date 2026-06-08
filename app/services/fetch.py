from __future__ import annotations

import httpx

from app.config import AppConfig
from app.constants import HIGHLIGHT_LIMIT, HTTP_TIMEOUT, USER_AGENT, ZENDESK_HIGHLIGHT_LIMIT
from app.services.normalize import finalize_entry, pick_recent
from app.services.parsers.base import ParsedEntry
from app.services.parsers.capacities_html import parse_capacities_html
from app.services.parsers.cursor_html import parse_cursor_html
from app.services.parsers.github_releases import parse_github_releases, parse_github_releases_simple
from app.services.parsers.microsoft_store_html import parse_microsoft_store_html
from app.services.parsers.notion_html import parse_notion_html
from app.services.parsers.rss import parse_rss
from app.services.parsers.todoist_html import parse_todoist_html
from app.services.parsers.zendesk_articles import parse_zendesk_articles


class FetchError(Exception):
    def __init__(self, app_slug: str, message: str) -> None:
        self.app_slug = app_slug
        super().__init__(message)


async def fetch_source(app: AppConfig) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xml,text/xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = await client.get(app.source_url)
        if response.status_code >= 400:
            raise FetchError(app.slug, f"HTTP {response.status_code} for {app.source_url}")
        return response.text


def parse_recent(app: AppConfig, content: str) -> list[ParsedEntry]:
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

    highlight_limit = ZENDESK_HIGHLIGHT_LIMIT if app.parser == "zendesk_articles" else HIGHLIGHT_LIMIT
    entries = [finalize_entry(entry, highlight_limit=highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries
