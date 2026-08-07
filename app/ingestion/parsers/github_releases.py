from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import unquote

import feedparser
from bs4 import BeautifulSoup

from app.ingestion.github_tags import release_item_lookup_keys, release_tag_lookup_keys
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import date_from_dot_version, parse_datetime

BOILERPLATE_RE = re.compile(
    r"(microsoft store updates can sometimes lag|download|flathub|view release notes|please note:)",
    re.I,
)
PRERELEASE_HEURISTIC_RE = re.compile(
    r"-(?:dev\d|alpha|beta|rc(?:\.|\d|$))",
    re.I,
)


def is_likely_github_prerelease(title: str, url: str = "") -> bool:
    title = title.strip()
    if title.lower().startswith("pre-release"):
        return True
    combined = f"{title} {unquote(url)}"
    return bool(PRERELEASE_HEURISTIC_RE.search(combined))


def is_github_prerelease_item(item, prerelease_keys: frozenset[str] | None) -> bool:
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    if is_likely_github_prerelease(title, link):
        return True
    if not prerelease_keys:
        return False
    return any(key in prerelease_keys for key in release_item_lookup_keys(item))


def is_github_prerelease_entry(entry: ParsedEntry, prerelease_keys: frozenset[str] | None) -> bool:
    if is_likely_github_prerelease(entry.title, entry.source_url):
        return True
    if not prerelease_keys:
        return False
    return any(key in prerelease_keys for key in release_tag_lookup_keys(entry.title))


def apply_github_release_dates(
    entries: list[ParsedEntry],
    date_by_tag: dict[str, datetime],
) -> list[ParsedEntry]:
    if not date_by_tag:
        return entries

    enriched: list[ParsedEntry] = []
    for entry in entries:
        published = None
        for key in release_tag_lookup_keys(entry.title):
            published = date_by_tag.get(key)
            if published is not None:
                break
        if published is None:
            enriched.append(entry)
            continue
        enriched.append(replace(entry, published_at=published))
    return enriched


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


def entry_published_at(title: str, item) -> datetime:
    published = parse_datetime(item.get("published"))
    if published is not None:
        return published

    from_tag = date_from_dot_version(title)
    if from_tag is not None:
        return from_tag

    updated = parse_datetime(item.get("updated"))
    if updated is not None:
        return updated

    return datetime.now(timezone.utc).replace(tzinfo=None)


def entry_html(item) -> str:
    if item.get("content"):
        return item.content[0].value
    return item.get("summary") or item.get("description") or ""


def _extract_lines(soup: BeautifulSoup) -> list[str]:
    lines = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(" ", strip=True)]
    if lines:
        return lines

    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not BOILERPLATE_RE.search(p.get_text(" ", strip=True))
    ]
