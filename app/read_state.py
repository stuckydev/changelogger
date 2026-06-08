from __future__ import annotations

import re

ENTRY_ID_RE = re.compile(r"^[a-f0-9]{32}$")
READ_ENTRIES_MAX = 100


def parse_read_entries(raw: str | None) -> set[str]:
    if not raw or not raw.strip():
        return set()
    return {part.strip() for part in raw.split(",") if ENTRY_ID_RE.fullmatch(part.strip())}


def serialize_read_entries(ids: set[str] | list[str]) -> str:
    valid = [entry_id for entry_id in ids if ENTRY_ID_RE.fullmatch(entry_id)]
    return ",".join(valid[:READ_ENTRIES_MAX])


def normalize_read_entries(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for entry_id in ids:
        if not ENTRY_ID_RE.fullmatch(entry_id) or entry_id in seen:
            continue
        seen.add(entry_id)
        normalized.append(entry_id)
        if len(normalized) >= READ_ENTRIES_MAX:
            break
    return normalized
