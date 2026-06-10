from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import app.storage.models  # noqa: F401 — register ORM tables with Base.metadata

from app.settings import ENTRIES_PER_APP
from app.storage.db import Base
from app.storage.models import ChangelogEntry


def _changelog_entry_columns() -> set[str]:
    return {column.name for column in ChangelogEntry.__table__.columns}


def run_migrations(engine: Engine) -> None:
    _ensure_changelog_entries_schema(engine)
    Base.metadata.create_all(bind=engine)
    _trim_app_rows(engine)


def _ensure_changelog_entries_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "changelog_entries" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("changelog_entries")}
    if columns != _changelog_entry_columns():
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS changelog_entries"))


def _trim_app_rows(engine: Engine) -> None:
    inspector = inspect(engine)
    if "changelog_entries" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                DELETE FROM changelog_entries
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY app_slug ORDER BY published_at DESC
                               ) AS row_num
                        FROM changelog_entries
                    ) ranked
                    WHERE row_num <= {ENTRIES_PER_APP}
                )
                """
            )
        )
