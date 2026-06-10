from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from app.core.constants import ENTRIES_PER_APP, ZENDESK_HIGHLIGHT_LIMIT
from app.core.date_utils import parse_datetime_or_now
from app.domain.changelog import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

PREFERRED_HEADING_RE = re.compile(
    r"\b(general notes|game updates?|notable bug fixes|bug fixes?|gameplay|bugs)\b",
    re.I,
)
SECONDARY_HEADING_RE = re.compile(
    r"\b(general|collected changes)\b",
    re.I,
)
SKIP_HEADING_RE = re.compile(
    r"\b(alchemy balance|now available|bundles?|game update highlights)\b",
    re.I,
)
MARKETING_BULLET_RE = re.compile(
    r"\b(pre-?order|booster pack|mastery pass|event token|lands bundle|play bundle|pass bundle|pack bundle)\b",
    re.I,
)
VERSION_RE = re.compile(r"(\d{4}\.\d+(?:\.\d+)?)")


def parse_zendesk_articles(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    articles = data.get("articles") or []
    if not articles:
        return []

    sorted_articles = sorted(
        articles,
        key=lambda item: parse_datetime_or_now(item.get("created_at") or item.get("updated_at")),
        reverse=True,
    )

    results: list[ParsedEntry] = []
    for article in sorted_articles[:limit]:
        entry = _parse_article(article, fallback_source_url=source_url)
        if entry is not None:
            results.append(entry)

    return results


def _parse_article(article: dict, *, fallback_source_url: str) -> ParsedEntry | None:
    title = (article.get("title") or "Patch Notes").strip()
    body = article.get("body") or ""
    if not body.strip():
        return None

    highlights = _extract_highlights(body)
    if not highlights:
        return None

    published = parse_datetime_or_now(article.get("created_at") or article.get("updated_at"))
    source = (article.get("html_url") or fallback_source_url).strip()
    external_id = str(article.get("id") or _version_from_title(title) or title)
    categories = detect_categories(f"{title} {' '.join(highlights)}")

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        summary=highlights[0],
        categories=categories,
        source_url=source,
        published_at=published,
    )


def _extract_highlights(html: str, *, limit: int = ZENDESK_HIGHLIGHT_LIMIT) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    sections = _split_sections(soup)

    preferred: list[str] = []
    secondary: list[str] = []
    fallback: list[str] = []

    for heading, lines in sections:
        if SKIP_HEADING_RE.search(heading):
            continue
        filtered = _filter_bullets(lines)
        if not filtered:
            continue
        if PREFERRED_HEADING_RE.search(heading):
            preferred.extend(filtered)
        elif SECONDARY_HEADING_RE.search(heading):
            secondary.extend(filtered)
        else:
            fallback.extend(filtered)

    merged = preferred + secondary + fallback
    highlights = normalize_highlights(merged, limit=limit)
    if highlights:
        return highlights

    all_lines = _filter_bullets([li.get_text(" ", strip=True) for li in soup.find_all("li")])
    return normalize_highlights(all_lines, limit=limit)


def _split_sections(soup: BeautifulSoup) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_lines
        if current_lines:
            sections.append((current_heading, current_lines[:]))
        current_lines = []

    for node in soup.find_all(["h2", "h3", "ul", "p"]):
        if node.name in {"h2", "h3"}:
            flush()
            current_heading = node.get_text(" ", strip=True)
            continue

        if node.name == "ul":
            for li in node.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                if text:
                    current_lines.append(text)
            continue

        if node.name == "p" and (
            PREFERRED_HEADING_RE.search(current_heading) or SECONDARY_HEADING_RE.search(current_heading)
        ):
            text = node.get_text(" ", strip=True)
            if len(text) > 24:
                current_lines.append(text)

    flush()
    return sections


def _filter_bullets(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        text = line.strip()
        if not text or MARKETING_BULLET_RE.search(text):
            continue
        result.append(text)
    return result


def _version_from_title(title: str) -> str | None:
    match = VERSION_RE.search(title)
    return match.group(1) if match else None
