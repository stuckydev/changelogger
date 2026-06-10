from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from app.core.constants import ENTRIES_PER_APP, HIGHLIGHT_LIMIT
from app.services.summarize import normalize_highlights


@dataclass
class ParsedEntry:
    external_id: str
    title: str
    highlights: list[str]
    categories: list[str]
    source_url: str
    published_at: datetime
    summary: str = ""


def make_entry_id(app_slug: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{app_slug}:{external_id}".encode()).hexdigest()
    return digest[:32]


def highlights_to_json(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def highlights_from_json(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item) for item in data if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return []


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
