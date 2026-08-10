from __future__ import annotations

from typing import assert_never

from app.catalog.apps import AppConfig, EnrichType, ParserType
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import fetch_github_release_metadata
from app.ingestion.github_atom import apply_github_release_dates
from app.ingestion.normalize import finalize_entry
from app.ingestion.parsers.actual_blog import parse_actual_release_item
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry, pick_recent
from app.settings import ENTRIES_PER_APP


def _github_item_parser(enrich: EnrichType | None):
    match enrich:
        case "actual_blog":
            return parse_actual_release_item
        case None:
            return None
        case _:
            assert_never(enrich)


async def _parse_source(app: AppConfig, content: str) -> list[ParsedEntry]:
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
            github_metadata = None
            if app.github_repo:
                github_metadata = await fetch_github_release_metadata(app.github_repo)
            entries = await parse_github_releases(
                content,
                limit=limit,
                prerelease_keys=github_metadata.prerelease_keys if github_metadata else None,
                parse_item=_github_item_parser(app.enrich),
            )
            if github_metadata is not None:
                entries = apply_github_release_dates(entries, github_metadata.dates)
            return entries
        case "cursor_html":
            return parse_cursor_html(content, source_url=app.source_url, limit=limit)
        case "zendesk_articles":
            return parse_zendesk_articles(content, source_url=app.source_url, limit=limit)
        case _:
            assert_never(parser)


async def parse_recent(app: AppConfig, content: str) -> list[ParsedEntry]:
    try:
        entries = await _parse_source(app, content)
    except ValueError as exc:
        raise FetchError(app.slug, str(exc)) from exc

    entries = [finalize_entry(entry, highlight_limit=app.highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries
