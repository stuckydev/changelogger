from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.apps import AppConfig, load_apps
from app.settings import ENTRIES_PER_APP
from app.storage.models import AppSyncStatus, ChangelogEntry
from app.models.changelog import ParsedEntry, highlights_to_json, make_entry_id
from app.ingestion.errors import FetchError
from app.ingestion.fetcher import fetch_source
from app.ingestion.pipeline import parse_recent

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
            "highlights": highlights_to_json(entry.highlights),
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

    rows = list(
        db.scalars(
            select(ChangelogEntry)
            .where(ChangelogEntry.app_slug == app.slug)
            .order_by(ChangelogEntry.published_at.desc())
        )
    )
    kept_seen = 0
    for row in rows:
        if row.id not in kept_ids:
            db.delete(row)
            continue
        kept_seen += 1
        if kept_seen > ENTRIES_PER_APP:
            db.delete(row)


def record_sync_status(db: Session, app_slug: str, error: str | None) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = db.get(AppSyncStatus, app_slug)
    if row is None:
        db.add(AppSyncStatus(app_slug=app_slug, last_sync_at=now, last_error=error))
    else:
        row.last_sync_at = now
        row.last_error = error


def _persist_app_sync(
    db: Session,
    app: AppConfig,
    outcome: list[ParsedEntry] | FetchError,
) -> str | None:
    if isinstance(outcome, FetchError):
        record_sync_status(db, app.slug, str(outcome))
        db.commit()
        return str(outcome)

    try:
        upsert_recent(db, app, outcome)
        record_sync_status(db, app.slug, None)
        db.commit()
        logger.info("Synced %s: %s", app.slug, outcome[0].title)
        return None
    except Exception as exc:
        db.rollback()
        logger.exception("Upsert failed for %s: %s", app.slug, exc)
        message = str(exc)
        record_sync_status(db, app.slug, message)
        db.commit()
        return message


async def _fetch_entries(app: AppConfig) -> tuple[AppConfig, list[ParsedEntry] | FetchError]:
    try:
        content = await fetch_source(app)
        return app, await parse_recent(app, content)
    except FetchError as exc:
        return app, exc
    except Exception as exc:
        logger.exception("Sync failed for %s: %s", app.slug, exc)
        return app, FetchError(app.slug, str(exc))


async def sync_all(db: Session) -> dict[str, str | None]:
    """Return slug -> error message; None means success."""
    outcomes = await asyncio.gather(*[_fetch_entries(app) for app in load_apps()])

    results: dict[str, str | None] = {}
    for app, outcome in outcomes:
        try:
            results[app.slug] = _persist_app_sync(db, app, outcome)
        except Exception:
            db.rollback()
            logger.exception("Could not persist sync status for %s", app.slug)
            results[app.slug] = "Could not persist sync status"
    return results
