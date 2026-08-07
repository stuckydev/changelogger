from __future__ import annotations

import re
from urllib.parse import unquote

RELEASE_TAG_RE = re.compile(r"(?:pre-)?release\s+(v?[\d][\w.\-]*)", re.I)
BARE_TAG_RE = re.compile(r"^(v?[\d][\w.\-]*)$", re.I)


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
