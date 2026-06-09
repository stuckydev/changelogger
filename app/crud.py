from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ChangelogEntry


def list_entries(
    db: Session,
    *,
    app_slugs: list[str] | None = None,
    limit: int = 50,
) -> list[ChangelogEntry]:
    if app_slugs is not None and not app_slugs:
        return []

    stmt = select(ChangelogEntry).order_by(ChangelogEntry.published_at.desc()).limit(limit)
    if app_slugs:
        stmt = stmt.where(ChangelogEntry.app_slug.in_(app_slugs))
    return list(db.scalars(stmt))


def count_entries(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(ChangelogEntry)) or 0


def latest_sync(db: Session) -> datetime | None:
    return db.scalar(select(ChangelogEntry.fetched_at).order_by(ChangelogEntry.fetched_at.desc()).limit(1))
