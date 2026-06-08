from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChangelogEntry(Base):
    __tablename__ = "changelog_entries"
    __table_args__ = (
        UniqueConstraint("app_slug", "external_id", name="uq_entry_app_external"),
        Index("ix_entries_published", "published_at"),
        Index("ix_entries_app_published", "app_slug", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    highlights: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    categories: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
