from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Literal

import yaml

from app.infra.logos import thumb_url_for_slug
from app.ingestion.parsers.microsoft_store_html import microsoft_store_en_url
from app.settings import CONFIG_PATH, STATIC_DIR

AppCategory = Literal["saas", "selfhosted", "games", "utilities"]

CATEGORY_LABELS: dict[AppCategory, str] = {
    "saas": "SaaS",
    "selfhosted": "Selfhosted",
    "games": "Game",
    "utilities": "Utility",
}

CATEGORY_ORDER: tuple[AppCategory, ...] = ("saas", "selfhosted", "games", "utilities")

ParserType = Literal[
    "rss",
    "todoist_html",
    "notion_html",
    "github_releases",
    "capacities_html",
    "cursor_html",
    "microsoft_store_html",
    "zendesk_articles",
]


def github_releases_url(github_repo: str) -> str:
    return f"https://github.com/{github_repo.strip('/')}/releases.atom"


def _resolve_logo_src(slug: str, logo_url: str | None) -> str:
    if logo_url:
        return logo_url
    logo_dir = STATIC_DIR / "logos"
    for extension in (".png", ".ico", ".webp", ".svg"):
        path = logo_dir / f"{slug}{extension}"
        if path.exists():
            if extension != ".svg":
                thumb = thumb_url_for_slug(slug)
                if thumb:
                    return thumb
            return f"/static/logos/{slug}{extension}"
    return f"/static/logos/{slug}.png"


@dataclass(frozen=True)
class AppConfig:
    slug: str
    name: str
    source_url: str
    parser: ParserType
    category: AppCategory
    subtitle: str | None = None
    github_repo: str | None = None
    logo_url: str | None = None
    github_simple: bool = False

    @property
    def logo_src(self) -> str:
        return _resolve_logo_src(self.slug, self.logo_url)

    @property
    def display_name(self) -> str:
        if self.subtitle:
            return f"{self.name} ({self.subtitle})"
        return self.name

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS[self.category]


@lru_cache
def load_apps() -> tuple[AppConfig, ...]:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    apps: list[AppConfig] = []
    for item in raw.get("apps", []):
        parser: ParserType = item["parser"]
        github_repo = item.get("github_repo")
        source_url = item.get("source_url")
        if parser == "github_releases":
            if not github_repo and not source_url:
                raise ValueError(f"App '{item['slug']}': github_releases requires github_repo or source_url")
            if not source_url and github_repo:
                source_url = github_releases_url(github_repo)
        elif not source_url:
            raise ValueError(f"App '{item['slug']}': source_url is required")
        if parser == "microsoft_store_html":
            source_url = microsoft_store_en_url(source_url)

        slug = item["slug"]
        raw_category = item.get("category", "utilities")
        if raw_category not in CATEGORY_LABELS:
            raise ValueError(
                f"App '{slug}': category must be one of {', '.join(CATEGORY_ORDER)}, got '{raw_category}'"
            )
        category: AppCategory = raw_category
        apps.append(
            AppConfig(
                slug=slug,
                name=item["name"],
                source_url=source_url,
                parser=parser,
                category=category,
                subtitle=item.get("subtitle"),
                github_repo=github_repo,
                logo_url=item.get("logo_url"),
                github_simple=bool(item.get("github_simple")),
            )
        )
    return tuple(apps)


@lru_cache
def apps_by_slug() -> dict[str, AppConfig]:
    return {app.slug: app for app in load_apps()}


def all_slugs() -> list[str]:
    return [app.slug for app in load_apps()]


def _sort_apps_by_last_update(
    apps: list[AppConfig],
    last_updates: dict[str, datetime],
) -> list[AppConfig]:
    return sorted(
        apps,
        key=lambda app: (
            -(last_updates[app.slug].timestamp()) if app.slug in last_updates else float("inf"),
            app.slug,
        ),
    )


def apps_sorted_by_last_update(
    last_updates: dict[str, datetime] | None = None,
) -> tuple[AppConfig, ...]:
    updates = last_updates or {}
    return tuple(_sort_apps_by_last_update(list(load_apps()), updates))
