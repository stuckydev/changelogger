from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, NavigableString, Tag

from app.services.parsers.base import ParsedEntry
from app.services.summarize import detect_categories, normalize_highlights

DATE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$"
)


def parse_todoist_html(content: str, *, source_url: str) -> ParsedEntry | None:
    soup = BeautifulSoup(content, "html.parser")
    main = soup.find("article") or soup.find("main") or soup.body
    if not main:
        return None

    current_date: datetime | None = None
    buffer_lines: list[str] = []
    headline: str | None = None
    finished = False

    for node in main.descendants:
        if finished:
            break

        if isinstance(node, Tag) and node.name == "h2":
            heading = node.get_text(" ", strip=True)
            if DATE_RE.match(heading):
                if current_date is not None:
                    finished = True
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

    if current_date is None or not buffer_lines:
        return None

    title = headline or _feature_title(buffer_lines) or f"Update on {_format_date(current_date)}"
    highlights = normalize_highlights(_prioritize_lines(buffer_lines))
    categories = detect_categories(f"{title} {' '.join(highlights)}")
    external_id = f"{current_date.date().isoformat()}:{title[:80]}"

    return ParsedEntry(
        external_id=external_id,
        title=title,
        highlights=highlights,
        summary=highlights[0] if highlights else title,
        categories=categories,
        source_url=source_url,
        published_at=current_date,
    )


def _prioritize_lines(lines: list[str]) -> list[str]:
    featured = [line for line in lines if "📣" in line or line.startswith("⭐") or line.lower().startswith("new:")]
    fixes = [line for line in lines if "🐛" in line or "fix" in line.lower()]
    rest = [line for line in lines if line not in featured and line not in fixes]
    return featured + rest + fixes


def _parse_heading_date(value: str) -> datetime:
    return datetime.strptime(value, "%B %d, %Y")


def _format_date(value: datetime) -> str:
    return value.strftime("%b %d, %Y")


def _is_feature_heading(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("new:") or "📣" in value or lowered.startswith("new ")


def _clean_heading(value: str) -> str:
    cleaned = re.sub(r"^📣\s*", "", value.strip())
    cleaned = re.sub(r"^New:\s*", "", cleaned, flags=re.I)
    return cleaned.strip()


def _feature_title(lines: list[str]) -> str | None:
    for line in lines:
        if "📣" in line or line.lower().startswith("new:"):
            return _clean_heading(line)
        if line.startswith("⭐"):
            return line.lstrip("⭐ ").strip()
    return None
