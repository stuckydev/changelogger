from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChangelogEntry


def list_entries(
    db: Session,
    *,
    app_slugs: list[str] | None = None,
    limit: int = 50,
) -> list[ChangelogEntry]:
    stmt = select(ChangelogEntry).order_by(ChangelogEntry.published_at.desc()).limit(limit)
    if app_slugs:
        stmt = (
            select(ChangelogEntry)
            .where(ChangelogEntry.app_slug.in_(app_slugs))
            .order_by(ChangelogEntry.published_at.desc())
            .limit(limit)
        )
    return list(db.scalars(stmt))


def latest_sync(db: Session) -> datetime | None:
    row = db.scalar(select(ChangelogEntry.fetched_at).order_by(ChangelogEntry.fetched_at.desc()).limit(1))
    return row
