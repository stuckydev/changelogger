from __future__ import annotations

import hashlib
import json
import re

from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import parse_datetime
from app.models.changelog import ParsedEntry
from app.ingestion.normalize import normalize_highlights

PAGE_METADATA_RE = re.compile(r"window\.pageMetadata\s*=\s*(\{.*?\});\s*\n", re.S)
STORE_DETAIL_RE = re.compile(r"apps\.microsoft\.com/detail/([a-zA-Z0-9]+)", re.I)


def microsoft_store_en_url(source_url: str) -> str:
    """Always fetch English release notes; Store locale query params override Accept-Language."""
    match = STORE_DETAIL_RE.search(source_url)
    if not match:
        return source_url
    return f"https://apps.microsoft.com/detail/{match.group(1)}?hl=en-US&gl=US"


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

    package_updated = parse_datetime(data.get("packageLastUpdateDateUtc"))
    store_updated = parse_datetime(data.get("lastUpdateDateUtc"))
    published = package_updated or store_updated
    if published is None:
        return []

    version = (data.get("version") or "").strip()
    short_title = (data.get("shortTitle") or "Update").strip()
    title = f"{short_title} {version}".strip() if version else f"{short_title} Update"

    product_id = (data.get("productId") or "store").strip().lower()
    notes_key = hashlib.sha256(raw_notes.encode()).hexdigest()[:16]
    external_id = f"{product_id}:{version}" if version else f"{product_id}:{notes_key}"
    return [
        ParsedEntry(
            external_id=external_id,
            title=title,
            highlights=highlights[:limit * 3],
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
