from __future__ import annotations

import re

from bs4 import BeautifulSoup

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


def extract_mtgarena_highlights(html: str) -> list[str]:
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
    if merged:
        return merged

    return _filter_bullets([li.get_text(" ", strip=True) for li in soup.find_all("li")])


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
