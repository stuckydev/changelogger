from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import AppConfig, load_apps
from app.models import ChangelogEntry
from app.services.fetch import FetchError, fetch_source, parse_latest
from app.services.parsers.base import ParsedEntry, highlights_to_json, make_entry_id

logger = logging.getLogger(__name__)


def upsert_latest(db: Session, app: AppConfig, entry: ParsedEntry) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entry_id = make_entry_id(app.slug)

    db.execute(delete(ChangelogEntry).where(ChangelogEntry.app_slug == app.slug))
    db.add(
        ChangelogEntry(
            id=entry_id,
            app_slug=app.slug,
            external_id=entry.external_id,
            title=entry.title,
            summary=entry.summary,
            highlights=highlights_to_json(entry.highlights),
            categories=",".join(entry.categories),
            source_url=entry.source_url,
            published_at=entry.published_at,
            fetched_at=now,
        )
    )
    db.commit()


async def sync_app(db: Session, app: AppConfig) -> str:
    try:
        content = await fetch_source(app)
        entry = parse_latest(app, content)
        upsert_latest(db, app, entry)
        return entry.title
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
