from __future__ import annotations

import logging
from typing import assert_never

from app.catalog.apps import AppConfig, ParserType
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import GitHubReleaseDraft, draft_from_release, fetch_github_releases, fetch_source, fetch_steam_news, fetch_text
from app.ingestion.normalize import finalize_entry
from app.ingestion.parsers.actual_blog import blog_url_if_needed, parse_actual_draft
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.mtgarena_notes import extract_mtgarena_highlights
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.steam_news import parse_steam_news, steam_appid_from_url
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry, pick_recent
from app.settings import ENTRIES_PER_APP

logger = logging.getLogger(__name__)


async def parse_recent(app: AppConfig) -> list[ParsedEntry]:
    try:
        entries = await _parse_source(app)
    except ValueError as exc:
        raise FetchError(str(exc)) from exc

    entries = [finalize_entry(entry, highlight_limit=app.highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError("No changelog entry found in source")
    return entries


async def _github_drafts(repo: str) -> list[GitHubReleaseDraft]:
    releases = await fetch_github_releases(repo)
    return [draft for release in releases if (draft := draft_from_release(release))]


async def _parse_actual_blog(app: AppConfig, limit: int) -> list[ParsedEntry]:
    repo = app.github_repo
    assert repo is not None
    drafts = await _github_drafts(repo)
    results: list[ParsedEntry] = []
    for draft in drafts:
        blog_html = None
        url = blog_url_if_needed(draft)
        if url:
            try:
                blog_html = await fetch_text(url)
            except FetchError:
                logger.warning("Actual blog fetch failed for %s (%s)", app.slug, url)
        try:
            results.append(parse_actual_draft(draft, blog_html))
        except ValueError as exc:
            logger.warning(
                "Skipped Actual release %s for %s: %s",
                draft.tag_name or draft.external_id,
                app.slug,
                exc,
            )
            continue
        if len(results) >= limit:
            break
    return results


async def _parse_source(app: AppConfig) -> list[ParsedEntry]:
    limit = ENTRIES_PER_APP
    parser: ParserType = app.parser
    match parser:
        case "github_releases":
            repo = app.github_repo
            assert repo is not None
            return parse_github_releases(await _github_drafts(repo), limit=limit)
        case "actual_blog":
            return await _parse_actual_blog(app, limit)
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
            )
        case "mtgarena_notes":
            return parse_zendesk_articles(
                await fetch_source(app),
                source_url=app.source_url,
                limit=limit,
                extract_highlights=extract_mtgarena_highlights,
            )
        case "steam_news":
            appid = steam_appid_from_url(app.source_url)
            if not appid:
                raise ValueError(f"App '{app.slug}': steam_news source_url must contain a Steam app id")
            payload = await fetch_steam_news(appid)
            return parse_steam_news(payload, source_url=app.source_url, limit=limit)
        case _:
            assert_never(parser)
