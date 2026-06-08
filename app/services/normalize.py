from __future__ import annotations

from app.constants import ENTRIES_PER_APP
from app.services.parsers.base import ParsedEntry
from app.services.summarize import normalize_highlights


def pick_recent(entries: list[ParsedEntry], *, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    if not entries:
        return []

    ordered = sorted(entries, key=lambda item: item.published_at, reverse=True)
    seen_external_ids: set[str] = set()
    result: list[ParsedEntry] = []
    for entry in ordered:
        if entry.external_id in seen_external_ids:
            continue
        seen_external_ids.add(entry.external_id)
        result.append(entry)
        if len(result) >= limit:
            break
    return result


def finalize_entry(entry: ParsedEntry, *, highlight_limit: int | None = None) -> ParsedEntry:
    highlights = normalize_highlights(entry.highlights, limit=highlight_limit or HIGHLIGHT_LIMIT)
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
