from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.constants import ENTRIES_PER_APP
from app.services.normalize import pick_recent
from app.services.parsers.base import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$", re.I)
SKIP_H2 = {"recent continuous improvements"}


def parse_capacities_html(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    soup = BeautifulSoup(content, "html.parser")
    base = source_url.rstrip("/")
    candidates: list[ParsedEntry] = []

    for h2 in soup.find_all("h2"):
        title = h2.get_text(" ", strip=True)
        if title.lower() in SKIP_H2:
            continue

        match = VERSION_RE.match(title.strip())
        if not match:
            continue

        version = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        published = _release_date(h2)
        anchor_id = _anchor_id(h2)
        bullets = _extract_section_lines(h2)
        entry_url = f"{base}/#{anchor_id}" if anchor_id else base + "/"
        highlights = normalize_highlights(bullets)
        if not highlights:
            continue

        categories = detect_categories(f"{title} {' '.join(highlights)}")
        external_id = f"{title}:{published.date().isoformat()}"

        candidates.append(
            ParsedEntry(
                external_id=external_id,
                title=title,
                highlights=highlights,
                summary=highlights[0],
                categories=categories,
                source_url=entry_url,
                published_at=published,
            )
        )

    return pick_recent(candidates, limit=limit)


def _release_date(h2) -> datetime:
    for time_el in [h2.find_previous("time"), h2.find_next("time")]:
        if time_el is None:
            continue
        raw = time_el.get("datetime") or time_el.get_text(strip=True)
        if not raw:
            continue
        try:
            if "T" in raw:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _anchor_id(h2) -> str | None:
    if h2.get("id"):
        return h2["id"]
    parent = h2.parent
    for _ in range(4):
        if parent is None:
            break
        if parent.get("id"):
            return parent["id"]
        parent = parent.parent
    return None


def _extract_section_lines(h2) -> list[str]:
    lines: list[str] = []
    node = h2.find_next_sibling()

    while node is not None:
        if node.name == "h2":
            heading = node.get_text(" ", strip=True)
            if VERSION_RE.match(heading.strip()) or heading.lower() in SKIP_H2:
                break

        if node.name in {"h3", "h4"}:
            text = node.get_text(" ", strip=True)
            if text and not text.lower().startswith("discover"):
                lines.append(text)
        elif node.name == "ul":
            for li in node.find_all("li", recursive=False):
                text = li.get_text(" ", strip=True)
                if text:
                    lines.append(text)
        elif node.name == "p":
            text = node.get_text(" ", strip=True)
            if len(text) > 24:
                lines.append(text)

        node = node.find_next_sibling()

    return lines
