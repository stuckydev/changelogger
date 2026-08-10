from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.catalog.apps import AppConfig, load_apps
from app.ingestion.errors import FetchError
from app.ingestion.pipeline import parse_recent
from app.models.changelog import ParsedEntry, highlights_to_json, make_entry_id
from app.storage.entries_repo import save_last_new_entries_count
from app.storage.models import AppSyncStatus, ChangelogEntry

logger = logging.getLogger(__name__)


def replace_recent(db: Session, app: AppConfig, entries: list[ParsedEntry]) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    previous_ids = set(
        db.scalars(select(ChangelogEntry.external_id).where(ChangelogEntry.app_slug == app.slug))
    )
    new_count = sum(1 for entry in entries if entry.external_id not in previous_ids)

    db.execute(delete(ChangelogEntry).where(ChangelogEntry.app_slug == app.slug))
    for entry in entries:
        db.add(
            ChangelogEntry(
                id=make_entry_id(app.slug, entry.external_id),
                app_slug=app.slug,
                external_id=entry.external_id,
                title=entry.title,
                highlights=highlights_to_json(entry.highlights),
                source_url=entry.source_url,
                published_at=entry.published_at,
                fetched_at=now,
            )
        )
    return new_count


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
) -> tuple[str | None, int]:
    if isinstance(outcome, FetchError):
        record_sync_status(db, app.slug, str(outcome))
        db.commit()
        return str(outcome), 0

    try:
        new_count = replace_recent(db, app, outcome)
        record_sync_status(db, app.slug, None)
        db.commit()
        logger.info("Synced %s: %s", app.slug, outcome[0].title)
        return None, new_count
    except Exception as exc:
        db.rollback()
        logger.exception("Replace failed for %s: %s", app.slug, exc)
        message = str(exc)
        record_sync_status(db, app.slug, message)
        db.commit()
        return message, 0


async def _fetch_entries(app: AppConfig) -> tuple[AppConfig, list[ParsedEntry] | FetchError]:
    try:
        return app, await parse_recent(app)
    except FetchError as exc:
        return app, exc
    except Exception as exc:
        logger.exception("Sync failed for %s: %s", app.slug, exc)
        return app, FetchError(app.slug, str(exc))


async def sync_all(db: Session) -> dict[str, str | None]:
    """Return slug -> error message; None means success."""
    outcomes = await asyncio.gather(*[_fetch_entries(app) for app in load_apps()])

    results: dict[str, str | None] = {}
    new_entries_count = 0
    for app, outcome in outcomes:
        try:
            error, new_count = _persist_app_sync(db, app, outcome)
            results[app.slug] = error
            new_entries_count += new_count
        except Exception:
            db.rollback()
            logger.exception("Could not persist sync status for %s", app.slug)
            results[app.slug] = "Could not persist sync status"

    save_last_new_entries_count(db, new_entries_count)
    db.commit()
    return results
