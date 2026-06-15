from __future__ import annotations

from sqlalchemy.orm import Session

from app.storage.models import SyncMetadata

LAST_NEW_ENTRIES_KEY = "last_new_entries_count"


def save_last_new_entries_count(db: Session, count: int) -> None:
    row = db.get(SyncMetadata, LAST_NEW_ENTRIES_KEY)
    if row is None:
        db.add(SyncMetadata(key=LAST_NEW_ENTRIES_KEY, int_value=count))
    else:
        row.int_value = count
    db.commit()


def get_last_new_entries_count(db: Session) -> int | None:
    row = db.get(SyncMetadata, LAST_NEW_ENTRIES_KEY)
    return row.int_value if row else None
