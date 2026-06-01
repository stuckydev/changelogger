from __future__ import annotations

from app.services.parsers.base import ParsedEntry
from app.services.summarize import normalize_highlights


def pick_latest(entries: list[ParsedEntry]) -> ParsedEntry | None:
    if not entries:
        return None
    return max(entries, key=lambda item: item.published_at)


def finalize_entry(entry: ParsedEntry) -> ParsedEntry:
    highlights = normalize_highlights(entry.highlights)
    summary = entry.summary.strip()
    if not summary and highlights:
        summary = highlights[0]
    return ParsedEntry(
        external_id=entry.external_id,
        title=entry.title.strip() or "Latest update",
        highlights=highlights,
        categories=entry.categories,
        source_url=entry.source_url,
        published_at=entry.published_at,
        summary=summary,
    )
