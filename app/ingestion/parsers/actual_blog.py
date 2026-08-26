from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.fetcher import GitHubReleaseDraft
from app.ingestion.normalize import has_useful_highlights
from app.ingestion.parsers.github_releases import extract_body_lines, is_github_noise
from app.models.changelog import ParsedEntry

RELEASE_TITLE_PREFIX = re.compile(r"^(Pre-Release|Release)\s+", re.I)
PR_PREFIX_RE = re.compile(r"^#\d+\s*")
BLOG_PATH_RE = re.compile(r"actualbudget\.org/blog/release-", re.I)
VERSION_ONLY_RE = re.compile(r"^(?:release\s+)?v?[\d.]+$", re.I)
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)]+)\)")
CHANGE_HEADING_RE = re.compile(
    r"^(?:#{1,3}\s+)?(changes|changelog|what's changed|what changed)\s*$",
    re.I,
)


def detail_url_from_draft(draft: GitHubReleaseDraft) -> str | None:
    return _extract_detail_url(draft.body, RELEASE_TITLE_PREFIX.sub("", draft.title).strip() or draft.title)


def blog_url_if_needed(draft: GitHubReleaseDraft) -> str | None:
    if has_useful_highlights(_extract_change_lines(draft.body)):
        return None
    return detail_url_from_draft(draft)


def parse_actual_draft(draft: GitHubReleaseDraft, blog_html: str | None = None) -> ParsedEntry:
    version_title = RELEASE_TITLE_PREFIX.sub("", draft.title).strip() or draft.title
    detail_url = detail_url_from_draft(draft)
    raw_lines = _extract_change_lines(draft.body)
    page_title = ""
    if not has_useful_highlights(raw_lines) and blog_html:
        page_title, blog_lines = _parse_actual_blog(blog_html)
        if blog_lines:
            raw_lines = blog_lines

    if not has_useful_highlights(raw_lines):
        raise ValueError(f"No changelog highlights extracted (detail: {detail_url or draft.html_url})")

    title = _pick_display_title(version_title, page_title, raw_lines)
    return ParsedEntry(
        external_id=draft.external_id,
        title=title,
        highlights=raw_lines,
        source_url=detail_url or draft.html_url,
        published_at=draft.published_at,
    )


def _extract_change_lines(body: str) -> list[str]:
    if not body.strip():
        return []
    if "<h2" in body.lower() or "<h3" in body.lower() or "<ul" in body.lower():
        return _extract_change_lines_html(body)
    return _extract_change_lines_markdown(body)


def _extract_change_lines_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
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
    return extract_body_lines(html)


def _extract_change_lines_markdown(body: str) -> list[str]:
    lines: list[str] = []
    in_changes = False
    for raw in body.splitlines():
        stripped = raw.strip()
        heading = CHANGE_HEADING_RE.match(stripped)
        if heading:
            in_changes = True
            continue
        if in_changes and stripped.startswith("#"):
            break
        if in_changes and stripped.startswith(("- ", "* ", "+ ")):
            text = stripped[2:].strip()
            if text:
                lines.append(text)
    if lines:
        return lines
    return extract_body_lines(body)


def _extract_detail_url(body: str, title: str) -> str | None:
    version_hint = title.removeprefix("v").removeprefix("V").strip()
    blog_links: list[str] = []

    for match in MD_LINK_RE.finditer(body):
        text, href = match.group(1).lower(), match.group(2).strip()
        if BLOG_PATH_RE.search(href):
            blog_links.append(href.rstrip("/") + "/")
            continue
        if "release note" in text or "changelog" in text:
            return href

    if "<a" in body.lower():
        soup = BeautifulSoup(body, "html.parser")
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


def _parse_actual_blog(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    heading = main.find("h1")
    page_title = heading.get_text(" ", strip=True) if heading else ""

    preferred: list[str] = []
    from_prs: list[str] = []
    for li in main.find_all("li"):
        text = li.get_text(" ", strip=True)
        if not text:
            continue
        prefix = PR_PREFIX_RE.match(text)
        if prefix:
            text = text[prefix.end() :].strip()
            bucket = from_prs
        else:
            bucket = preferred
        if not text or len(text) < 18 or is_github_noise(text):
            continue
        bucket.append(text)

    return page_title, preferred or from_prs


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
