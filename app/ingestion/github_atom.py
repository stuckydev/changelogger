from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import unquote

from app.models.changelog import ParsedEntry
from app.utils.date_utils import date_from_dot_version, parse_datetime

RELEASE_TAG_RE = re.compile(r"(?:pre-)?release\s+(v?[\d][\w.\-]*)", re.I)
BARE_TAG_RE = re.compile(r"^(v?[\d][\w.\-]*)$", re.I)
PRERELEASE_HEURISTIC_RE = re.compile(
    r"-(?:dev\d|alpha|beta|rc(?:\.|\d|$))",
    re.I,
)
BOILERPLATE_RE = re.compile(
    r"(microsoft store updates can sometimes lag|download|flathub|view release notes|please note:)",
    re.I,
)


def _unique(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def tag_lookup_keys(tag: str) -> list[str]:
    tag = tag.strip()
    if not tag:
        return []
    lowered = tag.lower()
    bare = tag.lstrip("vV").lower()
    return _unique([lowered, bare, f"v{bare}"])


def release_tag_lookup_keys(title: str) -> list[str]:
    title = title.strip()
    keys: list[str] = []

    release_match = RELEASE_TAG_RE.search(title)
    if release_match:
        keys.extend(tag_lookup_keys(release_match.group(1)))

    bare_match = BARE_TAG_RE.match(title)
    if bare_match:
        keys.extend(tag_lookup_keys(bare_match.group(1)))

    return _unique(keys)


def release_item_lookup_keys(item) -> list[str]:
    keys: list[str] = []
    title = (item.get("title") or "").strip()
    if title:
        keys.extend(release_tag_lookup_keys(title))
    link = (item.get("link") or "").strip()
    if "/releases/tag/" in link:
        tag = unquote(link.rsplit("/releases/tag/", 1)[-1]).strip()
        keys.extend(tag_lookup_keys(tag))
        if "/" in tag:
            keys.extend(tag_lookup_keys(tag.rsplit("/", 1)[-1]))
    return _unique(keys)


def is_likely_github_prerelease(title: str, url: str = "") -> bool:
    title = title.strip()
    if title.lower().startswith("pre-release"):
        return True
    combined = f"{title} {unquote(url)}"
    return bool(PRERELEASE_HEURISTIC_RE.search(combined))


def is_github_prerelease_item(item, prerelease_keys: frozenset[str] | None) -> bool:
    title = (item.get("title") or "").strip()
    link = (item.get("link") or "").strip()
    if is_likely_github_prerelease(title, link):
        return True
    if not prerelease_keys:
        return False
    return any(key in prerelease_keys for key in release_item_lookup_keys(item))


def is_github_prerelease_entry(entry: ParsedEntry, prerelease_keys: frozenset[str] | None) -> bool:
    if is_likely_github_prerelease(entry.title, entry.source_url):
        return True
    if not prerelease_keys:
        return False
    return any(key in prerelease_keys for key in release_tag_lookup_keys(entry.title))


def apply_github_release_dates(
    entries: list[ParsedEntry],
    date_by_tag: dict[str, datetime],
) -> list[ParsedEntry]:
    if not date_by_tag:
        return entries

    enriched: list[ParsedEntry] = []
    for entry in entries:
        published = None
        for key in release_tag_lookup_keys(entry.title):
            published = date_by_tag.get(key)
            if published is not None:
                break
        if published is None:
            enriched.append(entry)
            continue
        enriched.append(replace(entry, published_at=published))
    return enriched


def entry_published_at(title: str, item) -> datetime:
    published = parse_datetime(item.get("published"))
    if published is not None:
        return published

    from_tag = date_from_dot_version(title)
    if from_tag is not None:
        return from_tag

    updated = parse_datetime(item.get("updated"))
    if updated is not None:
        return updated

    return datetime.now(timezone.utc).replace(tzinfo=None)


def entry_html(item) -> str:
    if item.get("content"):
        return item.content[0].value
    return item.get("summary") or item.get("description") or ""
