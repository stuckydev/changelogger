from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, NavigableString, Tag

from app.constants import ENTRIES_PER_APP
from app.services.parsers.base import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

DATE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$"
)
TITLE_PREFIX_RE = re.compile(r"^[\U0001F300-\U0001FAFF⭐📣🐛⚙️]+\s*")


def parse_todoist_html(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    soup = BeautifulSoup(content, "html.parser")
    main = soup.find("article") or soup.find("main") or soup.body
    if not main:
        return []

    sections: list[tuple[datetime, str | None, list[str]]] = []
    current_date: datetime | None = None
    headline: str | None = None
    buffer_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_date, headline, buffer_lines
        if current_date is not None and buffer_lines:
            sections.append((current_date, headline, buffer_lines[:]))
        headline = None
        buffer_lines = []

    for node in main.descendants:
        if len(sections) >= limit and current_date is None:
            break

        if isinstance(node, Tag) and node.name == "h2":
            heading = node.get_text(" ", strip=True)
            if DATE_RE.match(heading):
                flush_section()
                if len(sections) >= limit:
                    break
                current_date = _parse_heading_date(heading)
                continue

        if isinstance(node, Tag) and node.name == "h3" and current_date and _is_feature_heading(node.get_text(" ", strip=True)):
            headline = _clean_heading(node.get_text(" ", strip=True))
            continue

        if isinstance(node, Tag) and node.name == "li" and current_date:
            line = node.get_text(" ", strip=True)
            if line and not line.startswith("Latest versions"):
                buffer_lines.append(line)
            continue

        if isinstance(node, NavigableString) and current_date and headline is None:
            text = str(node).strip()
            if text.startswith("📣") or text.lower().startswith("new:"):
                headline = _clean_heading(text)

    flush_section()

    results: list[ParsedEntry] = []
    for current_date, headline, buffer_lines in sections[:limit]:
        title = headline or _format_entry_date(current_date)
        highlights = normalize_highlights(_prioritize_lines(buffer_lines))
        categories = detect_categories(f"{title} {' '.join(highlights)}")
        external_id = current_date.date().isoformat()

        results.append(
            ParsedEntry(
                external_id=external_id,
                title=title,
                highlights=highlights,
                summary=highlights[0] if highlights else title,
                categories=categories,
                source_url=source_url,
                published_at=current_date,
            )
        )

    return results


def _prioritize_lines(lines: list[str]) -> list[str]:
    featured = [line for line in lines if "📣" in line or line.startswith("⭐") or line.lower().startswith("new:")]
    fixes = [line for line in lines if "🐛" in line or "fix" in line.lower()]
    rest = [line for line in lines if line not in featured and line not in fixes]
    return featured + rest + fixes


def _parse_heading_date(value: str) -> datetime:
    return datetime.strptime(value, "%B %d, %Y")


def _format_entry_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def _is_feature_heading(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("new:") or "📣" in value or lowered.startswith("new ")


def _clean_heading(value: str) -> str:
    cleaned = TITLE_PREFIX_RE.sub("", value.strip())
    cleaned = re.sub(r"^New:\s*", "", cleaned, flags=re.I)
    return cleaned.strip()
