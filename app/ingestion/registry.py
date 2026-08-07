from __future__ import annotations

from typing import assert_never

from app.catalog.apps import AppConfig, ParserType
from app.ingestion.parsers.actual_releases import parse_actual_releases
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP


async def parse_with_registry(
    app: AppConfig,
    content: str,
    *,
    github_prerelease_keys: frozenset[str] | None = None,
) -> list[ParsedEntry]:
    limit = ENTRIES_PER_APP
    parser: ParserType = app.parser
    match parser:
        case "rss":
            return parse_rss(content, limit=limit)
        case "todoist_html":
            return parse_todoist_html(content, source_url=app.source_url, limit=limit)
        case "notion_html":
            return parse_notion_html(content, source_url=app.source_url, limit=limit)
        case "github_releases":
            return await parse_github_releases(
                content, limit=limit, prerelease_keys=github_prerelease_keys
            )
        case "actual_releases":
            return await parse_actual_releases(
                content, limit=limit, prerelease_keys=github_prerelease_keys
            )
        case "cursor_html":
            return parse_cursor_html(content, source_url=app.source_url, limit=limit)
        case "zendesk_articles":
            return parse_zendesk_articles(content, source_url=app.source_url, limit=limit)
        case _:
            assert_never(parser)
