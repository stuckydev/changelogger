from __future__ import annotations

import asyncio
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

    db.commit()


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
        if isinstance(outcome, FetchError):
            results[app.slug] = str(outcome)
            continue
        try:
            upsert_recent(db, app, outcome)
            results[app.slug] = None
            logger.info("Synced %s: %s", app.slug, outcome[0].title)
        except Exception as exc:
            logger.exception("Upsert failed for %s: %s", app.slug, exc)
            results[app.slug] = str(exc)
    return results
