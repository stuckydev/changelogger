"""Minimal parser/finalize self-check. Run: python scripts/check_parsers.py"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.catalog.apps import AppConfig
from app.ingestion import pipeline
from app.ingestion.fetcher import draft_from_release
from app.ingestion.normalize import finalize_entry, normalize_highlights
from app.ingestion.parsers.actual_blog import enrich_actual_blog
from app.ingestion.parsers.github_releases import parse_github_releases
from app.ingestion.parsers.mtgarena_notes import extract_mtgarena_highlights
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry
from app.presentation.view_models import build_feed_views


GITHUB_RELEASES = [
    {
        "id": 1,
        "tag_name": "v1.2.3",
        "name": "v1.2.3",
        "prerelease": False,
        "draft": False,
        "html_url": "https://github.com/example/repo/releases/tag/v1.2.3",
        "published_at": "2024-06-01T12:00:00Z",
        "body": "- Fixed the thing\n- Added another thing\n",
    },
    {
        "id": 2,
        "tag_name": "v1.2.3-beta.1",
        "name": "Pre-Release v1.2.3-beta.1",
        "prerelease": True,
        "draft": False,
        "html_url": "https://github.com/example/repo/releases/tag/v1.2.3-beta.1",
        "published_at": "2024-06-02T12:00:00Z",
        "body": "prerelease noise",
    },
]

RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Stable 1.0</title>
      <link>https://example.com/1.0</link>
      <guid>1.0</guid>
      <pubDate>Sat, 01 Jun 2024 12:00:00 GMT</pubDate>
      <description>&lt;ul&gt;&lt;li&gt;Ship it&lt;/li&gt;&lt;/ul&gt;</description>
    </item>
  </channel>
</rss>
"""

ZENDESK = """{
  "articles": [
    {
      "id": 42,
      "title": "MTG Arena Patch 2024.1",
      "html_url": "https://example.com/article/42",
      "created_at": "2024-06-01T12:00:00Z",
      "body": "<h2>Game Updates</h2><ul><li>Challenge queue fix</li><li>Pre-order booster pack sale</li></ul><h2>Bundles</h2><ul><li>Mastery Pass bundle</li></ul>"
    }
  ]
}"""

ACTUAL_RELEASE = {
    "id": 10,
    "tag_name": "v24.10.0",
    "name": "Release v24.10.0",
    "prerelease": False,
    "draft": False,
    "html_url": "https://github.com/actualbudget/actual/releases/tag/v24.10.0",
    "published_at": "2024-10-01T12:00:00Z",
    "body": "## Changes\n\n- Improved reconciliation for shared accounts\n",
}

NOTION_HTML = """
<html><body>
  <a href="/releases/2024-06-01/"><h2>Databases everywhere</h2></a>
  <article><p>A long enough paragraph about databases that should become a highlight.</p></article>
</body></html>
"""


def _check_github() -> None:
    drafts = [draft for release in GITHUB_RELEASES if (draft := draft_from_release(release))]
    entries = asyncio.run(parse_github_releases(drafts, limit=5))
    assert len(entries) == 1, entries
    assert entries[0].title == "v1.2.3"
    assert "Fixed the thing" in entries[0].highlights


def _check_rss() -> None:
    entries = parse_rss(RSS, limit=5)
    assert len(entries) == 1
    assert entries[0].highlights == ["Ship it"]


def _check_zendesk() -> None:
    entries = parse_zendesk_articles(
        ZENDESK,
        source_url="https://example.com",
        limit=5,
        extract_highlights=extract_mtgarena_highlights,
    )
    assert len(entries) == 1
    assert entries[0].highlights == ["Challenge queue fix"]


def _check_actual() -> None:
    draft = draft_from_release(ACTUAL_RELEASE)
    assert draft is not None
    entry = asyncio.run(enrich_actual_blog(draft))
    assert entry.title == "Improved reconciliation for shared accounts"
    assert "Improved reconciliation for shared accounts" in entry.highlights


def _check_notion() -> None:
    entries = parse_notion_html(NOTION_HTML, source_url="https://www.notion.com/releases", limit=5)
    assert len(entries) == 1
    assert entries[0].title == "Databases everywhere"
    assert entries[0].source_url == "https://www.notion.com/releases/2024-06-01/"
    assert any("databases" in line.lower() for line in entries[0].highlights)


def _check_finalize_owns_normalize() -> None:
    raw = ParsedEntry(
        external_id="1",
        title="  Title  ",
        highlights=["  Fixed the thing  ", "view release notes", "Fixed the thing"],
        source_url="https://example.com",
        published_at=datetime(2024, 6, 1),
    )
    finalized = finalize_entry(raw, highlight_limit=5)
    assert finalized.title == "Title"
    assert finalized.highlights == normalize_highlights(
        ["  Fixed the thing  ", "view release notes", "Fixed the thing"]
    )


def _check_pipeline() -> None:
    app = AppConfig(
        slug="demo",
        name="Demo",
        source_url="https://example.com",
        parser="rss",
        category="utilities",
    )

    async def _fake_fetch(_app):
        return RSS

    original = pipeline.fetch_source
    pipeline.fetch_source = _fake_fetch
    try:
        entries = asyncio.run(pipeline.parse_recent(app))
    finally:
        pipeline.fetch_source = original
    assert len(entries) == 1
    assert entries[0].highlights == ["Ship it"]


def _check_mtg_view() -> None:
    class Row:
        id = "row1"
        app_slug = "mtgarena"
        title = "Friends Challenge update"
        highlights = '["Draft queue fix"]'
        source_url = "https://example.com"
        published_at = datetime(2024, 6, 1)

    app = AppConfig(
        slug="mtgarena",
        name="MTG Arena",
        source_url="https://example.com",
        parser="zendesk_articles",
        category="games",
        enrich="mtgarena_notes",
        highlight_terms=("Challenge", "Friends", "Draft", "Sealed", "Limited"),
    )
    views = build_feed_views([Row()], {"mtgarena": app})
    assert len(views) == 1
    html = str(views[0].title_html)
    assert "<mark" in html and "Friends" in html and "Challenge" in html


def main() -> None:
    _check_github()
    _check_rss()
    _check_zendesk()
    _check_actual()
    _check_notion()
    _check_finalize_owns_normalize()
    _check_pipeline()
    _check_mtg_view()
    print("ok")


if __name__ == "__main__":
    main()
