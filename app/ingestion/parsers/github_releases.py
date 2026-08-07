from __future__ import annotations

import feedparser
from bs4 import BeautifulSoup

from app.ingestion.github_atom import (
    BOILERPLATE_RE,
    entry_html,
    entry_published_at,
    is_github_prerelease_item,
)
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP


async def parse_github_releases(
    content: str,
    *,
    limit: int = ENTRIES_PER_APP,
    prerelease_keys: frozenset[str] | None = None,
) -> list[ParsedEntry]:
    feed = feedparser.parse(content)
    if not feed.entries:
        return []

    results: list[ParsedEntry] = []
    for item in feed.entries:
        if is_github_prerelease_item(item, prerelease_keys):
            continue
        entry = _parse_release_item(item)
        if entry is not None:
            results.append(entry)
        if len(results) >= limit:
            break
    return results


def _parse_release_item(item) -> ParsedEntry | None:
    raw_title = (item.get("title") or "Release").strip()
    title = raw_title
    link = (item.get("link") or "").strip()
    external_id = (item.get("id") or link or title).strip()
    published = entry_published_at(raw_title, item)
    html = entry_html(item)
    soup = BeautifulSoup(html, "html.parser") if html else None
    raw_lines = _extract_lines(soup) if soup else []
    highlights = raw_lines if raw_lines else [title]

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        source_url=link or external_id,
        published_at=published,
    )


def _extract_lines(soup: BeautifulSoup) -> list[str]:
    lines = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(" ", strip=True)]
    if lines:
        return lines

    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not BOILERPLATE_RE.search(p.get_text(" ", strip=True))
    ]
