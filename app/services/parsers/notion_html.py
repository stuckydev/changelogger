from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.parsers.base import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

RELEASE_HREF_RE = re.compile(r"^/releases/(\d{4}-\d{2}-\d{2})/?$")


def parse_notion_html(content: str, *, source_url: str) -> ParsedEntry | None:
    soup = BeautifulSoup(content, "html.parser")
    base = source_url.rstrip("/")
    candidates: list[ParsedEntry] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        match = RELEASE_HREF_RE.match(href)
        if not match:
            continue

        date_str = match.group(1)
        if date_str in seen:
            continue

        title_el = link.find("h2") or link.find("h3")
        if not title_el:
            continue

        title = title_el.get_text(" ", strip=True)
        if not title:
            continue

        seen.add(date_str)
        entry_url = urljoin(base + "/", href.lstrip("/"))
        published = datetime.strptime(date_str, "%Y-%m-%d")
        article = _find_following_article(link)
        raw_lines = _extract_lines(article) if article else [title]
        highlights = normalize_highlights(raw_lines)
        categories = detect_categories(f"{title} {' '.join(highlights)}")
        external_id = f"{date_str}:{title[:80]}"

        candidates.append(
            ParsedEntry(
                external_id=external_id,
                title=title,
                highlights=highlights,
                summary=highlights[0] if highlights else title,
                categories=categories,
                source_url=entry_url,
                published_at=published,
            )
        )

    if not candidates:
        return None
    return max(candidates, key=lambda item: item.published_at)


def _extract_lines(article) -> list[str]:
    lines: list[str] = []
    for node in article.find_all(["h3", "p", "li"]):
        text = node.get_text(" ", strip=True)
        if not text or _is_noise(text):
            continue
        if node.name == "h3":
            lines.append(text)
            continue
        if len(text) >= 24:
            lines.append(text)
    return lines


def _is_noise(text: str) -> bool:
    lowered = text.lower()
    noise_markers = (
        "ad blocker",
        "preventing the video",
        "please watch it on youtube",
        "see the announcement on x",
        "learn more about",
        "watch the demo",
        "read the docs",
        "join the ",
        "waitlist",
    )
    return lowered in {"play", "finally!"} or any(marker in lowered for marker in noise_markers)


def _find_following_article(link) -> BeautifulSoup | None:
    container = link.find_parent("div")
    steps = 0
    while container is not None and steps < 8:
        article = container.find("article")
        if article:
            return article
        container = container.parent
        steps += 1
    return link.find_next("article")
