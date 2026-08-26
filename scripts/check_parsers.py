"""Minimal parser/finalize self-check. Run: python scripts/check_parsers.py"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.catalog.apps import AppConfig, load_apps
from app.ingestion import pipeline
from app.ingestion.fetcher import draft_from_release
from app.ingestion.normalize import finalize_entry, is_noise_line, normalize_highlights
from app.ingestion.parsers.actual_blog import parse_actual_draft
from app.ingestion.parsers.cursor_html import parse_cursor_html
from app.ingestion.parsers.github_releases import is_github_noise, parse_github_releases
from app.ingestion.parsers.mtgarena_notes import extract_mtgarena_highlights
from app.ingestion.parsers.notion_html import parse_notion_html
from app.ingestion.parsers.rss import parse_rss
from app.ingestion.parsers.steam_news import parse_steam_news
from app.ingestion.parsers.todoist_html import parse_todoist_html
from app.ingestion.parsers.zendesk_articles import parse_zendesk_articles
from app.models.changelog import ParsedEntry, StoredEntry
from app.presentation.highlight import highlight_terms
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

CURSOR_HTML = """
<html><body>
<article>
  <h1>Agent layout</h1>
  <span class="label">0.50.5</span>
  <time datetime="2024-06-01T12:00:00Z">Jun 1, 2024</time>
  <a href="/changelog/agent-layout">Changelog</a>
  <ul>
    <li>Fixed the sidebar crash on reload</li>
    <li>Play</li>
  </ul>
</article>
</body></html>
"""

TODOIST_HTML = """
<html><body>
<article>
  <h2>June 1, 2024</h2>
  <h3>New: Quick add</h3>
  <ul>
    <li>📣 Faster quick add</li>
    <li>🐛 Fixed a crash</li>
  </ul>
</article>
</body></html>
"""


def _app(**kwargs) -> AppConfig:
    kwargs.setdefault("logo_src", "/static/logos/demo.png")
    return AppConfig(**kwargs)


def _check_github() -> None:
    drafts = [draft for release in GITHUB_RELEASES if (draft := draft_from_release(release))]
    entries = parse_github_releases(drafts, limit=5)
    assert len(entries) == 1, entries
    assert entries[0].title == "v1.2.3"
    assert "Fixed the thing" in entries[0].highlights
    store_noise = "Microsoft Store updates can sometimes lag behind"
    assert is_github_noise(store_noise)
    assert not is_noise_line(store_noise)


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
    entry = parse_actual_draft(draft)
    assert entry.title == "Improved reconciliation for shared accounts"
    assert "Improved reconciliation for shared accounts" in entry.highlights

    patch_draft = draft_from_release(
        {
            "id": 11,
            "tag_name": "v26.8.1",
            "name": "v26.8.1",
            "prerelease": False,
            "draft": False,
            "html_url": "https://github.com/actualbudget/actual/releases/tag/v26.8.1",
            "published_at": "2024-10-02T12:00:00Z",
            "body": ":link: [View release notes](https://actualbudget.org/blog/release-26.8.1)\n",
        }
    )
    assert patch_draft is not None
    patch_blog = """
    <html><body><main>
      <h1>Release 26.8.1</h1>
      <ul>
        <li>#8628 Fix intermittent app freezes with 100% CPU usage — thanks matt-fidd</li>
        <li>#8662 Fix context menu showing on multi-account views — thanks matt-fidd</li>
        <li>announcement</li>
      </ul>
    </main></body></html>
    """
    patch = parse_actual_draft(patch_draft, patch_blog)
    assert patch.title == "Release 26.8.1"
    assert patch.highlights[0] == "Fix intermittent app freezes with 100% CPU usage — thanks matt-fidd"
    assert not any(line.startswith("#") for line in patch.highlights)

    mixed_blog = """
    <html><body><main>
      <h1>Release 26.8.0</h1>
      <ul>
        <li>Age of Money report released as a first-party feature</li>
        <li>#8540 Promote the Age of Money report to a stable feature — thanks youngcw</li>
      </ul>
    </main></body></html>
    """
    mixed = parse_actual_draft(patch_draft, mixed_blog)
    assert mixed.highlights == ["Age of Money report released as a first-party feature"]


def _check_notion() -> None:
    entries = parse_notion_html(NOTION_HTML, source_url="https://www.notion.com/releases", limit=5)
    assert len(entries) == 1
    assert entries[0].title == "Databases everywhere"
    assert entries[0].source_url == "https://www.notion.com/releases/2024-06-01/"
    assert any("databases" in line.lower() for line in entries[0].highlights)


def _check_cursor() -> None:
    entries = parse_cursor_html(CURSOR_HTML, source_url="https://cursor.com/changelog", limit=5)
    assert len(entries) == 1, entries
    assert entries[0].title == "0.50.5 · Agent layout"
    assert entries[0].source_url == "https://cursor.com/changelog/agent-layout"
    assert "Fixed the sidebar crash on reload" in entries[0].highlights
    assert "Play" not in entries[0].highlights


def _check_todoist() -> None:
    entries = parse_todoist_html(TODOIST_HTML, source_url="https://example.com/changelog", limit=5)
    assert len(entries) == 1, entries
    assert entries[0].title == "Quick add"
    assert entries[0].external_id == "2024-06-01"
    assert entries[0].highlights[0] == "📣 Faster quick add"
    assert "🐛 Fixed a crash" in entries[0].highlights


def _check_finalize_owns_normalize() -> None:
    raw = ParsedEntry(
        external_id="1",
        title="  Title  ",
        highlights=[
            "  Fixed the thing  ",
            "view release notes",
            "Fixed the thing",
            "**Search and responsiveness:** Better search",
        ],
        source_url="https://example.com",
        published_at=datetime(2024, 6, 1),
    )
    finalized = finalize_entry(raw, highlight_limit=5)
    assert finalized.title == "Title"
    assert "**" not in finalized.highlights[1]
    assert finalized.highlights == normalize_highlights(
        [
            "  Fixed the thing  ",
            "view release notes",
            "Fixed the thing",
            "**Search and responsiveness:** Better search",
        ]
    )
    assert finalized.highlights[1] == "Search and responsiveness: Better search"


def _check_pipeline() -> None:
    app = _app(
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


def _check_steam_news() -> None:
    payload = {
        "appnews": {
            "appid": 669330,
            "newsitems": [
                {
                    "gid": "1",
                    "title": "No title",
                    "contents": "[list][*][p]Should be ignored[/p][/*][/list]",
                    "date": 1700002000,
                    "appid": 669330,
                },
                {
                    "gid": "2",
                    "title": "Update 1.0",
                    "contents": (
                        "[list][*][p]\\[Crawler] HP 10 → 12[/p][/*]"
                        "[*][p]Fixed a bug[/p][/*][/list]"
                        "[h1][b]Feedback & Bug Reports[/b][/h1]"
                        "[list][*][p]Discord[/p][/*][/list]"
                    ),
                    "date": 1700001000,
                    "appid": 669330,
                },
            ],
        }
    }
    entries = parse_steam_news(
        json.dumps(payload),
        source_url="https://steamdb.info/app/669330/patchnotes/",
        limit=5,
    )
    assert len(entries) == 1, entries
    assert entries[0].title == "Update 1.0"
    assert entries[0].highlights == ["[Crawler] HP 10 → 12", "Fixed a bug"]
    assert entries[0].source_url == "https://store.steampowered.com/news/app/669330/"


def _check_mtg_view() -> None:
    row = StoredEntry(
        id="row1",
        app_slug="mtgarena",
        title="Friends Challenge update",
        highlights=["Draft queue fix"],
        source_url="https://example.com",
        published_at=datetime(2024, 6, 1),
    )
    app = _app(
        slug="mtgarena",
        name="MTG Arena",
        source_url="https://example.com",
        parser="mtgarena_notes",
        category="games",
        highlight_terms=("Challenge", "Friends", "Draft", "Sealed", "Limited"),
    )
    views = build_feed_views([row], {"mtgarena": app})
    assert len(views) == 1
    html = str(views[0].title_html)
    assert "<mark" not in html
    assert '<span class="feed-card__keyword">Friends</span>' in html
    assert "Challenge" in html
    dirty = highlight_terms("**Search and responsiveness:** Better", ())
    assert str(dirty) == "Search and responsiveness: Better"


def _check_catalog() -> None:
    apps = {app.slug: app for app in load_apps()}
    assert apps["actual"].parser == "actual_blog"
    assert apps["mtgarena"].parser == "mtgarena_notes"
    assert apps["actual"].github_repo == "actualbudget/actual"


def main() -> None:
    _check_github()
    _check_rss()
    _check_zendesk()
    _check_actual()
    _check_notion()
    _check_cursor()
    _check_todoist()
    _check_finalize_owns_normalize()
    _check_pipeline()
    _check_steam_news()
    _check_mtg_view()
    _check_catalog()
    print("ok")


if __name__ == "__main__":
    main()
