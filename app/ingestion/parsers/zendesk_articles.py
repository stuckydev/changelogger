from __future__ import annotations

import json
from collections.abc import Callable

from bs4 import BeautifulSoup

from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import parse_datetime_or_now

HighlightExtractor = Callable[[str], list[str]]


def parse_zendesk_articles(
    content: str,
    *,
    source_url: str,
    limit: int = ENTRIES_PER_APP,
    extract_highlights: HighlightExtractor | None = None,
) -> list[ParsedEntry]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    articles = data.get("articles") or []
    if not articles:
        return []

    highlight_fn = extract_highlights or extract_all_bullets
    sorted_articles = sorted(
        articles,
        key=lambda item: parse_datetime_or_now(item.get("created_at") or item.get("updated_at")),
        reverse=True,
    )

    results: list[ParsedEntry] = []
    for article in sorted_articles[:limit]:
        entry = _parse_article(article, fallback_source_url=source_url, extract_highlights=highlight_fn)
        if entry is not None:
            results.append(entry)

    return results


def extract_all_bullets(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [li.get_text(" ", strip=True) for li in soup.find_all("li") if li.get_text(" ", strip=True)]


def _parse_article(
    article: dict,
    *,
    fallback_source_url: str,
    extract_highlights: HighlightExtractor,
) -> ParsedEntry | None:
    title = (article.get("title") or "Patch Notes").strip()
    body = article.get("body") or ""
    if not body.strip():
        return None

    highlights = extract_highlights(body)
    if not highlights:
        return None

    article_id = article.get("id")
    if article_id is None:
        return None

    published = parse_datetime_or_now(article.get("created_at") or article.get("updated_at"))
    source = (article.get("html_url") or fallback_source_url).strip()
    return ParsedEntry(
        external_id=str(article_id),
        title=title,
        highlights=highlights,
        source_url=source,
        published_at=published,
    )
