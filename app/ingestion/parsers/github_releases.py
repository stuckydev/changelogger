from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.fetcher import GitHubReleaseDraft
from app.ingestion.normalize import is_noise_line
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP

_MD_BULLET_RE = re.compile(r"^[-*+]\s+(.+)$")
_MD_HEADING_RE = re.compile(r"^#{1,3}\s+(.*)$")
_IMAGE_ONLY_RE = re.compile(r"^!\[[^\]]*\]\([^)]+\)$")
_GITHUB_NOISE_RE = re.compile(
    r"(update sponsors readme|chore:\s*update sponsors|github-actions\[bot\]|"
    r"please watch it on youtube|see the announcement on x|"
    r"microsoft store updates can sometimes lag|flathub|"
    r"ad blocker|preventing the video|watch the demo|"
    r"join the |waitlist)",
    re.I,
)


def is_github_noise(text: str) -> bool:
    return is_noise_line(text) or bool(_GITHUB_NOISE_RE.search(text))


def parse_github_releases(
    drafts: list[GitHubReleaseDraft],
    *,
    limit: int = ENTRIES_PER_APP,
) -> list[ParsedEntry]:
    results: list[ParsedEntry] = []
    for draft in drafts:
        results.append(entry_from_draft(draft))
        if len(results) >= limit:
            break
    return results


def entry_from_draft(draft: GitHubReleaseDraft) -> ParsedEntry:
    lines = extract_body_lines(draft.body)
    highlights = lines if lines else [draft.title]
    return ParsedEntry(
        external_id=draft.external_id,
        title=draft.title,
        highlights=highlights,
        source_url=draft.html_url,
        published_at=draft.published_at,
    )


def extract_body_lines(body: str) -> list[str]:
    if not body.strip():
        return []
    if "<li" in body.lower() or "<p" in body.lower():
        return _extract_html_lines(body)
    return _extract_markdown_lines(body)


def _extract_html_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    lines = [
        li.get_text(" ", strip=True)
        for li in soup.find_all("li")
        if li.get_text(" ", strip=True) and not is_github_noise(li.get_text(" ", strip=True))
    ]
    if lines:
        return lines
    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not is_github_noise(p.get_text(" ", strip=True))
    ]


def _extract_markdown_lines(body: str) -> list[str]:
    lines: list[str] = []
    parts: list[str] = []

    def flush() -> None:
        if not parts:
            return
        text = " ".join(parts).strip()
        parts.clear()
        if text and not is_github_noise(text):
            lines.append(text)

    for raw in body.splitlines():
        stripped = raw.strip()
        match = _MD_BULLET_RE.match(stripped)
        if match:
            flush()
            parts.append(match.group(1).strip())
            continue
        if parts and raw[:1].isspace() and stripped and not _IMAGE_ONLY_RE.match(stripped):
            parts.append(stripped)
    flush()
    if lines:
        return lines
    return [
        line.strip()
        for line in body.splitlines()
        if len(line.strip()) >= 24
        and not _MD_HEADING_RE.match(line.strip())
        and not is_github_noise(line.strip())
    ]
