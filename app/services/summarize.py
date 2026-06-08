from __future__ import annotations

import re

from app.constants import HIGHLIGHT_LIMIT, HIGHLIGHT_MAX_CHARS

CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Fix", re.compile(r"\b(fixed|fix|bug|resolved)\b|🐛", re.I)),
    ("Update", re.compile(r"\b(new:|feature|introduc|launch|added|support for|improv|enhanc|streamlin|update|optimiz|refactor|security|cve|vulnerabilit)\b|📣|⭐|⚙️", re.I)),
]

NOISE_RE = re.compile(
    r"(update sponsors readme|chore:\s*update sponsors|github-actions\[bot\]|"
    r"please watch it on youtube|see the announcement on x|learn more about|"
    r"view release notes|latest versions at the time of publishing|"
    r"see the full release notes for details)",
    re.I,
)


def detect_categories(text: str) -> list[str]:
    found: list[str] = []
    for label, pattern in CATEGORY_PATTERNS:
        if pattern.search(text):
            found.append(label)
    if not found:
        found.append("Update")
    return found[:2]


def clean_bullet(text: str) -> str:
    cleaned = re.sub(r"\[\[[!#\w-]+\]\]", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned.strip(" -•\t"))
    if not cleaned:
        return ""
    if len(cleaned) > HIGHLIGHT_MAX_CHARS:
        cleaned = cleaned[: HIGHLIGHT_MAX_CHARS - 1].rsplit(" ", 1)[0] + "…"
    return cleaned


def normalize_highlights(lines: list[str], *, limit: int = HIGHLIGHT_LIMIT) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for line in lines:
        bullet = clean_bullet(line)
        if not bullet or NOISE_RE.search(bullet):
            continue
        key = bullet.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(bullet)
        if len(result) >= limit:
            break

    return result


def compact_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return sentences[0].strip() if sentences else cleaned
