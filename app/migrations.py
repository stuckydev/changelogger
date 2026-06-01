from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import Base


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if "changelog_entries" not in inspector.get_table_names():
        Base.metadata.create_all(bind=engine)
        return

    columns = {column["name"] for column in inspector.get_columns("changelog_entries")}
    if "highlights" in columns:
        _dedupe_app_rows(engine)
        return

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS changelog_entries"))
    Base.metadata.create_all(bind=engine)


def _dedupe_app_rows(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM changelog_entries
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY app_slug ORDER BY published_at DESC
                               ) AS row_num
                        FROM changelog_entries
                    ) ranked
                    WHERE row_num = 1
                )
                """
            )
        )
