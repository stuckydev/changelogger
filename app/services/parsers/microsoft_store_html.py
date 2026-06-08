from __future__ import annotations

import json
import re

from app.constants import ENTRIES_PER_APP
from app.date_utils import parse_datetime
from app.services.parsers.base import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

PAGE_METADATA_RE = re.compile(r"window\.pageMetadata\s*=\s*(\{.*?\});\s*\n", re.S)


def parse_microsoft_store_html(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    match = PAGE_METADATA_RE.search(content)
    if not match:
        return []

    data = json.loads(match.group(1))
    notes = data.get("notes") or []
    raw_notes = notes[0] if notes else ""
    highlights = normalize_highlights(_split_notes(raw_notes))
    if not highlights:
        return []

    published = parse_datetime(data.get("lastUpdateDateUtc") or data.get("packageLastUpdateDateUtc"))
    if published is None:
        return []

    version = (data.get("version") or "").strip()
    short_title = (data.get("shortTitle") or "Update").strip()
    title = f"{short_title} {version}".strip() if version else f"{short_title} Update"

    product_id = (data.get("productId") or "store").strip().lower()
    external_id = f"{product_id}:{published.date().isoformat()}"
    categories = detect_categories(f"{title} {' '.join(highlights)}")

    return [
        ParsedEntry(
            external_id=external_id,
            title=title,
            highlights=highlights[:limit * 3],
            summary=highlights[0],
            categories=categories,
            source_url=source_url,
            published_at=published,
        )
    ][:limit]


def _split_notes(raw: str) -> list[str]:
    if not raw.strip():
        return []

    lines: list[str] = []
    for part in raw.replace("\r\n", "\n").split("\n"):
        text = part.strip().lstrip("•").lstrip("\u2022").strip()
        if text:
            lines.append(text)
    return lines
