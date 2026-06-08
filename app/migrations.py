from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

import app.models  # noqa: F401 — register ORM tables with Base.metadata

from app.constants import ENTRIES_PER_APP
from app.db import Base
from app.services.parsers.base import make_entry_id


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if "changelog_entries" not in inspector.get_table_names():
        Base.metadata.create_all(bind=engine)
        return

    columns = {column["name"] for column in inspector.get_columns("changelog_entries")}
    if "highlights" not in columns:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS changelog_entries"))
        Base.metadata.create_all(bind=engine)
        return

    if _uses_single_entry_schema(inspector):
        _migrate_to_multi_entry_schema(engine)

    _trim_app_rows(engine)


def _uses_single_entry_schema(inspector) -> bool:
    for constraint in inspector.get_unique_constraints("changelog_entries"):
        if constraint["name"] == "uq_entry_app" and constraint["column_names"] == ["app_slug"]:
            return True
    return False


def _migrate_to_multi_entry_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT app_slug, external_id, title, summary, highlights, categories,
                       source_url, published_at, fetched_at
                FROM changelog_entries
                """
            )
        ).mappings().all()

        conn.execute(text("DROP TABLE changelog_entries"))

    Base.metadata.create_all(bind=engine)

    if not rows:
        return

    with engine.begin() as conn:
        for row in rows:
            entry_id = make_entry_id(row["app_slug"], row["external_id"])
            conn.execute(
                text(
                    """
                    INSERT INTO changelog_entries (
                        id, app_slug, external_id, title, summary, highlights, categories,
                        source_url, published_at, fetched_at
                    ) VALUES (
                        :id, :app_slug, :external_id, :title, :summary, :highlights, :categories,
                        :source_url, :published_at, :fetched_at
                    )
                    """
                ),
                {"id": entry_id, **row},
            )


def _trim_app_rows(engine: Engine) -> None:
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
