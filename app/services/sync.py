from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import AppConfig, load_apps
from app.constants import ENTRIES_PER_APP
from app.models import ChangelogEntry
from app.services.fetch import FetchError, fetch_source, parse_recent
from app.services.parsers.base import ParsedEntry, highlights_to_json, make_entry_id

logger = logging.getLogger(__name__)


def upsert_recent(db: Session, app: AppConfig, entries: list[ParsedEntry]) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    kept_ids: set[str] = set()

    for entry in entries:
        entry_id = make_entry_id(app.slug, entry.external_id)
        kept_ids.add(entry_id)
        existing = db.get(ChangelogEntry, entry_id)
        payload = {
            "app_slug": app.slug,
            "external_id": entry.external_id,
            "title": entry.title,
            "summary": entry.summary,
            "highlights": highlights_to_json(entry.highlights),
            "categories": ",".join(entry.categories),
            "source_url": entry.source_url,
            "published_at": entry.published_at,
            "fetched_at": now,
        }
        if existing is None:
            db.add(ChangelogEntry(id=entry_id, **payload))
        else:
            for key, value in payload.items():
                setattr(existing, key, value)

    db.flush()

    for row in db.scalars(select(ChangelogEntry).where(ChangelogEntry.app_slug == app.slug)):
        if row.id not in kept_ids:
            db.delete(row)

    rows = list(
        db.scalars(
            select(ChangelogEntry)
            .where(ChangelogEntry.app_slug == app.slug)
            .order_by(ChangelogEntry.published_at.desc())
        )
    )
    for stale in rows[ENTRIES_PER_APP:]:
        db.delete(stale)

    db.commit()


async def sync_app(db: Session, app: AppConfig) -> str:
    try:
        content = await fetch_source(app)
        entries = parse_recent(app, content)
        upsert_recent(db, app, entries)
        return entries[0].title
    except Exception as exc:
        logger.exception("Sync failed for %s: %s", app.slug, exc)
        raise FetchError(app.slug, str(exc)) from exc


async def sync_all(db: Session) -> dict[str, str]:
    results: dict[str, str] = {}
    for app in load_apps():
        try:
            results[app.slug] = await sync_app(db, app)
        except FetchError as exc:
            results[app.slug] = str(exc)
    return results
