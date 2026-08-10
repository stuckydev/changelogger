from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.fetcher import GitHubReleaseDraft
from app.ingestion.normalize import is_noise_line
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP

_MD_BULLET_RE = re.compile(r"^[-*+]\s+(.+)$")
_MD_HEADING_RE = re.compile(r"^#{1,3}\s+(.*)$")


async def parse_github_releases(
    drafts: list[GitHubReleaseDraft],
    *,
    limit: int = ENTRIES_PER_APP,
    enrich=None,
) -> list[ParsedEntry]:
    results: list[ParsedEntry] = []
    for draft in drafts:
        if enrich is not None:
            try:
                entry = await enrich(draft)
            except ValueError:
                continue
        else:
            entry = entry_from_draft(draft)
        if entry is not None:
            results.append(entry)
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
        if li.get_text(" ", strip=True) and not is_noise_line(li.get_text(" ", strip=True))
    ]
    if lines:
        return lines
    return [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(" ", strip=True) and not is_noise_line(p.get_text(" ", strip=True))
    ]


def _extract_markdown_lines(body: str) -> list[str]:
    lines: list[str] = []
    for raw in body.splitlines():
        match = _MD_BULLET_RE.match(raw.strip())
        if not match:
            continue
        text = match.group(1).strip()
        if text and not is_noise_line(text):
            lines.append(text)
    if lines:
        return lines
    return [
        line.strip()
        for line in body.splitlines()
        if len(line.strip()) >= 24
        and not _MD_HEADING_RE.match(line.strip())
        and not is_noise_line(line.strip())
    ]