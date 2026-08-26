from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.ingestion.normalize import is_noise_line
from app.models.changelog import ParsedEntry
from app.settings import ENTRIES_PER_APP
from app.utils.date_utils import now_utc_naive

STEAM_APPID_RE = re.compile(r"(?:/app/|[?&]appid=)(\d+)", re.I)
UNTITLED_RE = re.compile(r"^no title$", re.I)
FEEDBACK_RE = re.compile(r"\[h[1-3]\](?:\[b\])?\s*Feedback\b", re.I)
LIST_ITEM_RE = re.compile(r"\[\*\](.*?)\[/\*\]", re.S)
ESCAPED_BRACKET_RE = re.compile(r"\\\[([^\]]+)\]")
IMG_RE = re.compile(r"\[img[^\]]*\](?:\[/img\])?", re.I)
URL_RE = re.compile(r"\[url(?:=[^\]]+)?\](.*?)\[/url\]", re.I | re.S)
BBCODE_RE = re.compile(r"\[/?[a-z][a-z0-9]*(?:[=\s][^\]]*)?\]", re.I)
PARAGRAPH_RE = re.compile(r"\[p[^\]]*\](.*?)\[/p\]", re.S)


def steam_appid_from_url(url: str) -> str | None:
    match = STEAM_APPID_RE.search(url or "")
    return match.group(1) if match else None


def parse_steam_news(content: str, *, source_url: str, limit: int = ENTRIES_PER_APP) -> list[ParsedEntry]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    items = (data.get("appnews") or {}).get("newsitems") or []
    if not items:
        return []

    sorted_items = sorted(items, key=_item_timestamp, reverse=True)
    results: list[ParsedEntry] = []
    for item in sorted_items:
        entry = _parse_item(item, fallback_source_url=source_url)
        if entry is None:
            continue
        results.append(entry)
        if len(results) >= limit:
            break
    return results


def _parse_item(item: dict, *, fallback_source_url: str) -> ParsedEntry | None:
    title = (item.get("title") or "").strip()
    if not title or UNTITLED_RE.match(title):
        return None

    body = item.get("contents") or ""
    highlights = _highlights(body)
    if not highlights:
        highlights = [title]

    gid = str(item.get("gid") or "").strip()
    if not gid:
        return None

    appid = item.get("appid")
    source = (
        f"https://store.steampowered.com/news/app/{appid}/"
        if appid
        else (item.get("url") or fallback_source_url).strip()
    )
    return ParsedEntry(
        external_id=gid,
        title=title,
        highlights=highlights,
        source_url=source,
        published_at=_published_at(item),
    )


def _highlights(body: str) -> list[str]:
    cut = FEEDBACK_RE.split(body, maxsplit=1)[0]
    items = [_plain(raw) for raw in LIST_ITEM_RE.findall(cut)]
    items = [line for line in items if line and not is_noise_line(line)]
    if items:
        return items
    if "<li" in cut.lower():
        soup = BeautifulSoup(cut, "html.parser")
        return [
            text
            for li in soup.find_all("li")
            if (text := li.get_text(" ", strip=True)) and not is_noise_line(text)
        ]
    return [
        para
        for raw in PARAGRAPH_RE.findall(cut)
        if (para := _plain(raw)) and len(para) >= 24 and not is_noise_line(para)
    ]


def _plain(text: str) -> str:
    saved: list[str] = []

    def stash(match: re.Match[str]) -> str:
        saved.append(match.group(1))
        return f"@@{len(saved) - 1}@@"

    text = ESCAPED_BRACKET_RE.sub(stash, text)
    text = IMG_RE.sub(" ", text)
    text = URL_RE.sub(r"\1", text)
    text = BBCODE_RE.sub(" ", text)
    for index, inner in enumerate(saved):
        text = text.replace(f"@@{index}@@", f"[{inner}]")
    return re.sub(r"\s+", " ", text).strip()


def _item_timestamp(item: dict) -> float:
    raw = item.get("date")
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _published_at(item: dict) -> datetime:
    raw = item.get("date")
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(int(raw), timezone.utc).replace(tzinfo=None)
    try:
        return datetime.fromtimestamp(int(raw), timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError):
        return now_utc_naive()
