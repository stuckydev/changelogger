from __future__ import annotations

from typing import assert_never

from app.catalog.apps import AppConfig, EnrichType, ParserType
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import draft_from_release, fetch_github_releases, fetch_source
from app.ingestion.normalize import finalize_entry
from app.ingestion.parsers.actual_blog import enrich_actual_blog
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.mtgarena_notes import extract_mtgarena_highlights
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry, pick_recent
from app.settings import ENTRIES_PER_APP


def _github_enricher(enrich: EnrichType | None):
    match enrich:
        case "actual_blog":
            return enrich_actual_blog
        case "mtgarena_notes":
            return None
        case None:
            return None
        case _:
            assert_never(enrich)


def _zendesk_highlight_extractor(enrich: EnrichType | None):
    match enrich:
        case "mtgarena_notes":
            return extract_mtgarena_highlights
        case "actual_blog" | None:
            return None
        case _:
            assert_never(enrich)


async def parse_recent(app: AppConfig) -> list[ParsedEntry]:
    try:
        entries = await _parse_source(app)
    except ValueError as exc:
        raise FetchError(app.slug, str(exc)) from exc

    entries = [finalize_entry(entry, highlight_limit=app.highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries


async def _parse_source(app: AppConfig) -> list[ParsedEntry]:
    limit = ENTRIES_PER_APP
    parser: ParserType = app.parser
    match parser:
        case "github_releases":
            if not app.github_repo:
                raise ValueError(f"App '{app.slug}': github_releases requires github_repo")
            try:
                releases = await fetch_github_releases(app.github_repo)
            except FetchError as exc:
                raise FetchError(app.slug, str(exc)) from exc
            drafts = [draft for release in releases if (draft := draft_from_release(release))]
            return await parse_github_releases(
                drafts,
                limit=limit,
                enrich=_github_enricher(app.enrich),
            )
        case "rss":
            return parse_rss(await fetch_source(app), limit=limit)
        case "todoist_html":
            return parse_todoist_html(
                await fetch_source(app), source_url=app.source_url, limit=limit
            )
        case "notion_html":
            return parse_notion_html(
                await fetch_source(app), source_url=app.source_url, limit=limit
            )
        case "cursor_html":
            return parse_cursor_html(
                await fetch_source(app), source_url=app.source_url, limit=limit
            )
        case "zendesk_articles":
            return parse_zendesk_articles(
                await fetch_source(app),
                source_url=app.source_url,
                limit=limit,
                extract_highlights=_zendesk_highlight_extractor(app.enrich),
            )
        case _:
            assert_never(parser)
