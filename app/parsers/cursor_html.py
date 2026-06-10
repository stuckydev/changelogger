from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.core.constants import ENTRIES_PER_APP
from app.core.date_utils import parse_datetime
from app.domain.changelog import pick_recent
from app.domain.changelog import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

CHANGELOG_HREF_RE = re.compile(r"^/changelog/[^/?#]+$")
NOISE_RE = re.compile(
    r"(watch it on youtube|see the announcement|learn more about|read the docs|join the waitlist)",
    re.I,
)
CHANGELOG_HEADER_RE = re.compile(r"^\d+(?:\.\d+)*\s+[A-Za-z]{3}\s+\d{1,2},\s+\d{4}\s·\sChangelog$")


def parse_cursor_html(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    soup = BeautifulSoup(content, "html.parser")
    base = source_url.rstrip("/").removesuffix("/changelog")
    candidates: list[ParsedEntry] = []

    for article in soup.find_all("article"):
        entry = _parse_article(article, base=base)
        if entry is not None:
            candidates.append(entry)

    return pick_recent(candidates, limit=limit)


def _parse_article(article, *, base: str) -> ParsedEntry | None:
    h1 = article.find("h1")
    time_el = article.find("time")
    link = article.find("a", href=CHANGELOG_HREF_RE)
    if h1 is None or time_el is None or link is None:
        return None

    title_text = h1.get_text(" ", strip=True)
    if not title_text:
        return None

    published = parse_datetime(time_el.get("datetime") or time_el.get("dateTime"))
    if published is None:
        return None

    version_el = article.find("span", class_=re.compile(r"\blabel\b"))
    version = version_el.get_text(" ", strip=True) if version_el else ""
    display_title = f"{version} · {title_text}" if version else title_text

    href = link["href"].strip()
    entry_url = urljoin(base + "/", href.lstrip("/"))
    raw_lines = _extract_lines(article)
    highlights = normalize_highlights(raw_lines)
    if not highlights:
        highlights = [title_text]

    categories = detect_categories(f"{display_title} {' '.join(highlights)}")
    external_id = href.strip("/").split("/")[-1]

    return ParsedEntry(
        external_id=external_id,
        title=display_title,
        highlights=highlights,
        summary=highlights[0],
        categories=categories,
        source_url=entry_url,
        published_at=published,
    )


def _extract_lines(article) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()

    for li in article.find_all("li"):
        text = li.get_text(" ", strip=True)
        if text and text not in seen and not _is_noise(text):
            seen.add(text)
            lines.append(text)

    if lines:
        return lines

    for node in article.find_all(["h2", "h3", "p"]):
        text = node.get_text(" ", strip=True)
        if not text or text in seen or _is_noise(text):
            continue
        if node.name in {"h2", "h3"} or len(text) >= 24:
            seen.add(text)
            lines.append(text)

    return lines


def _is_noise(text: str) -> bool:
    lowered = text.lower()
    return (
        lowered in {"play", "changelog"}
        or bool(NOISE_RE.search(text))
        or bool(CHANGELOG_HEADER_RE.match(text))
        or (lowered.endswith("· changelog") and len(text) < 80)
    )
