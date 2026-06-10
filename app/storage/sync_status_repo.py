from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import AppSyncStatus


def sync_errors_by_slug(db: Session) -> dict[str, str]:
    rows = db.scalars(select(AppSyncStatus).where(AppSyncStatus.last_error.isnot(None)))
    return {row.app_slug: row.last_error for row in rows if row.last_error}
