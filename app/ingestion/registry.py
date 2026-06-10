from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

from app.catalog.apps import AppConfig, ParserType
from app.settings import ENTRIES_PER_APP
from app.models.changelog import ParsedEntry
from app.ingestion.parsers.capacities_html import parse_capacities_html
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.microsoft_store_html import parse_microsoft_store_html
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles

ParserResult = list[ParsedEntry] | Awaitable[list[ParsedEntry]]
ParserFn = Callable[..., ParserResult]

PARSERS: dict[ParserType, ParserFn] = {
    "rss": lambda content, *, app, limit: parse_rss(content, limit=limit),
    "todoist_html": lambda content, *, app, limit: parse_todoist_html(content, source_url=app.source_url, limit=limit),
    "notion_html": lambda content, *, app, limit: parse_notion_html(content, source_url=app.source_url, limit=limit),
    "github_releases": lambda content, *, app, limit: parse_github_releases(
        content, simple=app.github_simple, limit=limit
    ),
    "capacities_html": lambda content, *, app, limit: parse_capacities_html(content, source_url=app.source_url, limit=limit),
    "cursor_html": lambda content, *, app, limit: parse_cursor_html(content, source_url=app.source_url, limit=limit),
    "microsoft_store_html": lambda content, *, app, limit: parse_microsoft_store_html(
        content, source_url=app.source_url, limit=limit
    ),
    "zendesk_articles": lambda content, *, app, limit: parse_zendesk_articles(content, source_url=app.source_url, limit=limit),
}


async def parse_with_registry(app: AppConfig, content: str) -> list[ParsedEntry]:
    parser = PARSERS.get(app.parser)
    if parser is None:
        raise ValueError(f"Unknown parser: {app.parser}")

    result = parser(content, app=app, limit=ENTRIES_PER_APP)
    if inspect.isawaitable(result):
        return await result
    return result
