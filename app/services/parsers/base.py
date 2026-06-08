from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedEntry:
    external_id: str
    title: str
    highlights: list[str]
    categories: list[str]
    source_url: str
    published_at: datetime
    summary: str = ""


def make_entry_id(app_slug: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{app_slug}:{external_id}".encode()).hexdigest()
    return digest[:32]


def highlights_to_json(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def highlights_from_json(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item) for item in data if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return []
