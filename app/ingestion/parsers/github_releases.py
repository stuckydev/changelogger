from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import unquote

import feedparser
from bs4 import BeautifulSoup

from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import date_from_dot_version, parse_datetime
from app.models.changelog import ParsedEntry
from app.ingestion.normalize import normalize_highlights
from app.ingestion.release_enrichment import enrich_from_detail_url, pick_display_title

RELEASE_TITLE_PREFIX = re.compile(r"^(Pre-Release|Release)\s+", re.I)
RELEASE_TAG_RE = re.compile(r"(?:pre-)?release\s+(v?[\d][\w.\-]*)", re.I)
BARE_TAG_RE = re.compile(r"^(v?[\d][\w.\-]*)$", re.I)
BOILERPLATE_RE = re.compile(
    r"(microsoft store updates can sometimes lag|download|flathub|view release notes|please note:)",
    re.I,
)
USELESS_HIGHLIGHT_RE = re.compile(
    r"see the full release notes|view release notes|please note:",
    re.I,
)
PRERELEASE_HEURISTIC_RE = re.compile(
    r"-(?:dev\d|alpha|beta|rc(?:\.|\d|$))",
    re.I,
)


def release_tag_lookup_keys(title: str) -> list[str]:
    title = title.strip()
    keys: list[str] = []

    release_match = RELEASE_TAG_RE.search(title)
    if release_match:
        keys.extend(tag_lookup_keys(release_match.group(1)))

    bare_match = BARE_TAG_RE.match(title)
    if bare_match:
        keys.extend(tag_lookup_keys(bare_match.group(1)))

    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def tag_lookup_keys(tag: str) -> list[str]:
    tag = tag.strip()
    if not tag:
        return []
    lowered = tag.lower()
    bare = tag.lstrip("vV").lower()
    keys = [lowered, bare, f"v{bare}"]
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def release_item_lookup_keys(item) -> list[str]:
    keys: list[str] = []
    title = (item.get("title") or "").strip()
    if title:
        keys.extend(release_tag_lookup_keys(title))
    link = (item.get("link") or "").strip()
    if "/releases/tag/" in link:
        tag = unquote(link.rsplit("/releases/tag/", 1)[-1]).strip()
        keys.extend(tag_lookup_keys(tag))
        if "/" in tag:
            keys.extend(tag_lookup_keys(tag.rsplit("/", 1)[-1]))
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


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
    simple: bool = False,
    limit: int = ENTRIES_PER_APP,
    prerelease_keys: frozenset[str] | None = None,
) -> list[ParsedEntry]:
    feed = feedparser.parse(content)
    if not feed.entries:
        return []

    if simple:
        results: list[ParsedEntry] = []
        for item in feed.entries:
            if is_github_prerelease_item(item, prerelease_keys):
                continue
            entry = _parse_simple_release_item(item)
            if entry is not None:
                results.append(entry)
            if len(results) >= limit:
                break
        return results

    results: list[ParsedEntry] = []
    for item in _pick_recent_entries(feed.entries, limit=limit, prerelease_keys=prerelease_keys):
        try:
            entry = await _parse_release_item(item)
        except ValueError:
            continue
        if entry is not None:
            results.append(entry)
    return results


def _parse_simple_release_item(item) -> ParsedEntry | None:
    raw_title = (item.get("title") or "Release").strip()
    title = raw_title
    link = (item.get("link") or "").strip()
    external_id = (item.get("id") or link or title).strip()
    published = _entry_published_at(raw_title, item)
    html = _entry_html(item)
    soup = BeautifulSoup(html, "html.parser") if html else None
    raw_lines = _extract_simple_lines(soup) if soup else []
    highlights = normalize_highlights(raw_lines) if raw_lines else [title]

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        source_url=link or external_id,
        published_at=published,
    )


def _extract_simple_lines(soup: BeautifulSoup) -> list[str]:
    lines = [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(" ", strip=True)]
    if lines:
        return lines

    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not BOILERPLATE_RE.search(p.get_text(" ", strip=True))
    ]


async def _parse_release_item(item) -> ParsedEntry | None:
    raw_title = (item.get("title") or "Release").strip()
    version_title = RELEASE_TITLE_PREFIX.sub("", raw_title).strip() or raw_title
    link = (item.get("link") or "").strip()
    external_id = (item.get("id") or link or version_title).strip()
    published = _entry_published_at(raw_title, item)
    html = _entry_html(item)
    soup = BeautifulSoup(html, "html.parser") if html else None

    detail_url = _extract_detail_url(soup, version_title) if soup else None
    raw_lines = _extract_change_lines(soup) if soup else []
    page_title = ""
    if not _is_useful_lines(raw_lines) and detail_url:
        page_title, blog_lines = await enrich_from_detail_url(detail_url)
        if blog_lines:
            raw_lines = blog_lines

    highlights = normalize_highlights(raw_lines)
    if not highlights or _only_placeholder_highlights(highlights):
        raise ValueError(f"No changelog highlights extracted (detail: {detail_url or link})")

    title = pick_display_title(version_title, page_title, highlights)

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        source_url=detail_url or link or external_id,
        published_at=published,
    )


def _is_useful_lines(lines: list[str]) -> bool:
    if not lines:
        return False
    return any(line.strip() and not BOILERPLATE_RE.search(line) for line in lines)


def _only_placeholder_highlights(highlights: list[str]) -> bool:
    return len(highlights) == 1 and USELESS_HIGHLIGHT_RE.search(highlights[0])


def _entry_published_at(title: str, item) -> datetime:
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


def _pick_recent_entries(entries, *, limit: int = ENTRIES_PER_APP, prerelease_keys: frozenset[str] | None = None):
    picked = []
    for entry in entries:
        if is_github_prerelease_item(entry, prerelease_keys):
            continue
        picked.append(entry)
        if len(picked) >= limit:
            break
    return picked


def _entry_html(item) -> str:
    if item.get("content"):
        return item.content[0].value
    return item.get("summary") or item.get("description") or ""


def _extract_change_lines(soup: BeautifulSoup) -> list[str]:
    lines: list[str] = []
    for heading in soup.find_all(["h2", "h3"]):
        label = heading.get_text(" ", strip=True).lower()
        if label not in {"changes", "changelog", "what's changed", "what changed"}:
            continue
        sibling = heading.find_next_sibling()
        while sibling is not None and sibling.name not in {"h2", "h3"}:
            if sibling.name == "ul":
                for li in sibling.find_all("li", recursive=False):
                    text = li.get_text(" ", strip=True)
                    if text:
                        lines.append(text)
            sibling = sibling.find_next_sibling()
        if lines:
            break

    if lines:
        return lines

    paragraphs = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not BOILERPLATE_RE.search(p.get_text(" ", strip=True))
    ]
    return paragraphs


def _extract_detail_url(soup: BeautifulSoup, title: str) -> str | None:
    version_hint = title.removeprefix("v").removeprefix("V").strip()
    blog_links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        text = anchor.get_text(" ", strip=True).lower()
        if not href or href.startswith("#"):
            continue
        if "actualbudget.org/blog/release-" in href:
            blog_links.append(href.rstrip("/") + "/")
            continue
        if "release note" in text or "changelog" in text:
            return href

    for href in blog_links:
        if version_hint and version_hint in href:
            return href
    if blog_links:
        return blog_links[0]
    return None
