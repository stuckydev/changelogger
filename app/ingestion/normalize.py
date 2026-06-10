from __future__ import annotations

import re

from app.settings import HIGHLIGHT_LIMIT, HIGHLIGHT_MAX_CHARS
from app.models.changelog import ParsedEntry

NOISE_RE = re.compile(
    r"(update sponsors readme|chore:\s*update sponsors|github-actions\[bot\]|"
    r"please watch it on youtube|see the announcement on x|learn more about|"
    r"view release notes|latest versions at the time of publishing|"
    r"see the full release notes for details)",
    re.I,
)


def clean_bullet(text: str) -> str:
    cleaned = re.sub(r"\[\[[!#\w-]+\]\]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned.strip(" -•\t"))
    if not cleaned:
        return ""
    if len(cleaned) > HIGHLIGHT_MAX_CHARS:
        cleaned = cleaned[: HIGHLIGHT_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"
    return cleaned


def normalize_highlights(lines: list[str], *, limit: int = HIGHLIGHT_LIMIT) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for line in lines:
        bullet = clean_bullet(line)
        if not bullet or NOISE_RE.search(bullet):
            continue
        key = bullet.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(bullet)
        if len(result) >= limit:
            break

    return result


def finalize_entry(entry: ParsedEntry, *, highlight_limit: int | None = None) -> ParsedEntry:
    highlights = normalize_highlights(entry.highlights, limit=highlight_limit or HIGHLIGHT_LIMIT)
    return ParsedEntry(
        external_id=entry.external_id,
        title=entry.title.strip() or "Latest update",
        highlights=highlights,
        source_url=entry.source_url,
        published_at=entry.published_at,
    )
