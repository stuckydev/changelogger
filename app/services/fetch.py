from __future__ import annotations

import httpx

from app.config import AppConfig
from app.constants import HTTP_TIMEOUT, USER_AGENT
from app.services.normalize import finalize_entry
from app.services.parsers.base import ParsedEntry
from app.services.parsers.github_releases import parse_github_releases
from app.services.parsers.notion_html import parse_notion_html
from app.services.parsers.rss import parse_rss
from app.services.parsers.todoist_html import parse_todoist_html


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


def parse_latest(app: AppConfig, content: str) -> ParsedEntry | None:
    entry: ParsedEntry | None
    if app.parser == "rss":
        entry = parse_rss(content)
    elif app.parser == "todoist_html":
        entry = parse_todoist_html(content, source_url=app.source_url)
    elif app.parser == "notion_html":
        entry = parse_notion_html(content, source_url=app.source_url)
    elif app.parser == "github_releases":
        entry = parse_github_releases(content)
    else:
        raise FetchError(app.slug, f"Unknown parser: {app.parser}")

    if entry is None:
        raise FetchError(app.slug, "No changelog entry found in source")
    return finalize_entry(entry)
