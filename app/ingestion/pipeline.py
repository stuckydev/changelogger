from __future__ import annotations

from app.catalog.apps import AppConfig
from app.settings import HIGHLIGHT_LIMIT, ZENDESK_HIGHLIGHT_LIMIT
from app.models.changelog import ParsedEntry, pick_recent
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import fetch_github_release_dates
from app.ingestion.normalize import finalize_entry
from app.ingestion.parsers.github_releases import apply_github_release_dates
from app.ingestion.registry import parse_with_registry


async def parse_recent(app: AppConfig, content: str) -> list[ParsedEntry]:
    try:
        entries = await parse_with_registry(app, content)
    except ValueError as exc:
        raise FetchError(app.slug, str(exc)) from exc

    if app.parser == "github_releases" and app.github_repo:
        release_dates = await fetch_github_release_dates(app.github_repo)
        entries = apply_github_release_dates(entries, release_dates)

    highlight_limit = ZENDESK_HIGHLIGHT_LIMIT if app.parser == "zendesk_articles" else HIGHLIGHT_LIMIT
    entries = [finalize_entry(entry, highlight_limit=highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries
