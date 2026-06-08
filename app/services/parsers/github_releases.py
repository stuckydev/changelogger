from __future__ import annotations

import re
from datetime import datetime, timezone
import feedparser
from bs4 import BeautifulSoup

from app.constants import ENTRIES_PER_APP
from app.date_utils import date_from_dot_version, parse_datetime
from app.services.parsers.base import ParsedEntry
from app.services.release_notes_fetch import enrich_from_detail_url, pick_display_title
from app.services.summarize import compact_summary, detect_categories, normalize_highlights

RELEASE_TITLE_PREFIX = re.compile(r"^(Pre-Release|Release)\s+", re.I)
BOILERPLATE_RE = re.compile(
    r"(microsoft store updates can sometimes lag|download|flathub|view release notes|please note:)",
    re.I,
)
USELESS_HIGHLIGHT_RE = re.compile(
    r"see the full release notes|view release notes|please note:",
    re.I,
)


def parse_github_releases_simple(content: str, *, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    feed = feedparser.parse(content)
    if not feed.entries:
        return []

    results: list[ParsedEntry] = []
    for item in feed.entries[:limit]:
        entry = _parse_simple_release_item(item)
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
    categories = detect_categories(f"{title} {' '.join(highlights)}")

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        summary=highlights[0],
        categories=categories,
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


def parse_github_releases(content: str, *, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    feed = feedparser.parse(content)
    if not feed.entries:
        return []

    results: list[ParsedEntry] = []
    for item in _pick_recent_entries(feed.entries, limit=limit):
        try:
            entry = _parse_release_item(item)
        except ValueError:
            continue
        if entry is not None:
            results.append(entry)
    return results


def _parse_release_item(item) -> ParsedEntry | None:
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
        page_title, blog_lines = enrich_from_detail_url(detail_url)
        if blog_lines:
            raw_lines = blog_lines

    highlights = normalize_highlights(raw_lines)
    if not highlights or _only_placeholder_highlights(highlights):
        raise ValueError(f"No changelog highlights extracted (detail: {detail_url or link})")

    title = pick_display_title(version_title, page_title, highlights)
    summary = compact_summary(highlights[0])
    categories = detect_categories(f"{title} {' '.join(highlights)}")

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        summary=summary,
        categories=categories,
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


def _pick_recent_entries(entries, *, limit: int = ENTRIES_PER_APP):
    picked = []
    for entry in entries:
        title = (entry.get("title") or "").lower()
        if title.startswith("pre-release"):
            continue
        picked.append(entry)
        if len(picked) >= limit:
            break
    if not picked and entries:
        return entries[:limit]
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
