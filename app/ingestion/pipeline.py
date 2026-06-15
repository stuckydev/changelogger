from __future__ import annotations

from app.catalog.apps import AppConfig
from app.settings import HIGHLIGHT_LIMIT, ZENDESK_HIGHLIGHT_LIMIT
from app.models.changelog import ParsedEntry, pick_recent
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import fetch_github_release_metadata
from app.ingestion.normalize import finalize_entry
from app.ingestion.parsers.github_releases import apply_github_release_dates, is_github_prerelease_entry
from app.ingestion.registry import parse_with_registry


async def parse_recent(app: AppConfig, content: str) -> list[ParsedEntry]:
    github_metadata = None
    if app.parser == "github_releases" and app.github_repo:
        github_metadata = await fetch_github_release_metadata(app.github_repo)

    try:
        entries = await parse_with_registry(
            app,
            content,
            github_prerelease_keys=github_metadata.prerelease_keys if github_metadata else None,
        )
    except ValueError as exc:
        raise FetchError(app.slug, str(exc)) from exc

    if github_metadata is not None:
        entries = [
            entry for entry in entries if not is_github_prerelease_entry(entry, github_metadata.prerelease_keys)
        ]
        entries = apply_github_release_dates(entries, github_metadata.dates)

    highlight_limit = ZENDESK_HIGHLIGHT_LIMIT if app.parser == "zendesk_articles" else HIGHLIGHT_LIMIT
    entries = [finalize_entry(entry, highlight_limit=highlight_limit) for entry in entries]
    entries = pick_recent(entries)
    if not entries:
        raise FetchError(app.slug, "No changelog entry found in source")
    return entries
