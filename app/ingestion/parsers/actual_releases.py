from __future__ import annotations

import re

import feedparser
from bs4 import BeautifulSoup

from app.ingestion.github_atom import (
    BOILERPLATE_RE,
    entry_html,
    entry_published_at,
    is_github_prerelease_item,
)
from app.infra.http import get_http_client
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP

RELEASE_TITLE_PREFIX = re.compile(r"^(Pre-Release|Release)\s+", re.I)
USELESS_HIGHLIGHT_RE = re.compile(
    r"see the full release notes|view release notes|please note:",
    re.I,
)
PR_LINE_RE = re.compile(r"^#\d+")
BLOG_PATH_RE = re.compile(r"actualbudget\.org/blog/release-", re.I)
VERSION_ONLY_RE = re.compile(r"^(?:release\s+)?v?[\d.]+$", re.I)


async def parse_actual_releases(
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
        try:
            entry = await _parse_release_item(item)
        except ValueError:
            continue
        if entry is not None:
            results.append(entry)
        if len(results) >= limit:
            break
    return results


async def _parse_release_item(item) -> ParsedEntry | None:
    raw_title = (item.get("title") or "Release").strip()
    version_title = RELEASE_TITLE_PREFIX.sub("", raw_title).strip() or raw_title
    link = (item.get("link") or "").strip()
    external_id = (item.get("id") or link or version_title).strip()
    published = entry_published_at(raw_title, item)
    html = entry_html(item)
    soup = BeautifulSoup(html, "html.parser") if html else None

    detail_url = _extract_detail_url(soup, version_title) if soup else None
    raw_lines = _extract_change_lines(soup) if soup else []
    page_title = ""
    if not _is_useful_lines(raw_lines) and detail_url:
        page_title, blog_lines = await _enrich_from_blog(detail_url)
        if blog_lines:
            raw_lines = blog_lines

    if not raw_lines or _only_placeholder_highlights(raw_lines):
        raise ValueError(f"No changelog highlights extracted (detail: {detail_url or link})")

    title = _pick_display_title(version_title, page_title, raw_lines)
    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=raw_lines,
        source_url=detail_url or link or external_id,
        published_at=published,
    )


def _is_useful_lines(lines: list[str]) -> bool:
    if not lines:
        return False
    return any(line.strip() and not BOILERPLATE_RE.search(line) for line in lines)


def _only_placeholder_highlights(highlights: list[str]) -> bool:
    return len(highlights) == 1 and bool(USELESS_HIGHLIGHT_RE.search(highlights[0]))


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

    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not BOILERPLATE_RE.search(p.get_text(" ", strip=True))
    ]


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


async def _enrich_from_blog(detail_url: str) -> tuple[str, list[str]]:
    if not detail_url or not BLOG_PATH_RE.search(detail_url):
        return "", []
    if not detail_url.endswith("/"):
        detail_url = detail_url.rstrip("/") + "/"
    client = await get_http_client()
    response = await client.get(
        detail_url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return _parse_actual_blog(response.text)


def _parse_actual_blog(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    heading = main.find("h1")
    page_title = heading.get_text(" ", strip=True) if heading else ""

    lines: list[str] = []
    for li in main.find_all("li"):
        text = li.get_text(" ", strip=True)
        if not text or PR_LINE_RE.match(text) or len(text) < 18:
            continue
        lines.append(text)

    return page_title, lines


def _pick_display_title(version_title: str, page_title: str, highlights: list[str]) -> str:
    if page_title:
        return page_title
    if highlights and not VERSION_ONLY_RE.fullmatch(version_title.strip()):
        return version_title
    if highlights:
        first = highlights[0]
        if len(first) <= 72:
            return first
    return version_title
