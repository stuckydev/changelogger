from __future__ import annotations

import feedparser
from bs4 import BeautifulSoup

from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import parse_datetime_or_now


def parse_rss(content: str, *, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    feed = feedparser.parse(content)
    if not feed.entries:
        return []

    sorted_items = sorted(
        feed.entries,
        key=lambda entry: parse_datetime_or_now(entry.get("published") or entry.get("updated")),
        reverse=True,
    )

    results: list[ParsedEntry] = []
    for item in sorted_items:
        results.append(_parse_rss_item(item))
        if len(results) >= limit:
            break
    return results


def _parse_rss_item(item) -> ParsedEntry:
    title = (item.get("title") or "Release").strip()
    link = (item.get("link") or "").strip()
    external_id = (item.get("id") or link or title).strip()
    published = parse_datetime_or_now(item.get("published") or item.get("updated"))
    raw_summary = item.get("summary") or item.get("description") or title
    soup = BeautifulSoup(raw_summary, "html.parser")

    raw_lines = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(" ", strip=True)]
    if not raw_lines:
        plain = soup.get_text(" ", strip=True)
        raw_lines = [plain] if plain else [title]

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=raw_lines,
        source_url=link or external_id,
        published_at=published,
    )
