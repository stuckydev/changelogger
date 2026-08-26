from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Literal, get_args

import yaml

from app.infra.logos import resolve_logo_src
from app.settings import CONFIG_PATH, HIGHLIGHT_LIMIT

AppCategory = Literal["saas", "selfhosted", "games", "utilities"]

CATEGORY_LABELS: dict[AppCategory, str] = {
    "saas": "SaaS",
    "selfhosted": "Selfhosted",
    "games": "Game",
    "utilities": "Utility",
}

ParserType = Literal[
    "rss",
    "todoist_html",
    "notion_html",
    "github_releases",
    "cursor_html",
    "zendesk_articles",
    "steam_news",
    "actual_blog",
    "mtgarena_notes",
]

GITHUB_PARSERS: frozenset[str] = frozenset({"github_releases", "actual_blog"})
_PARSER_NAMES: frozenset[str] = frozenset(get_args(ParserType))


@dataclass(frozen=True)
class AppConfig:
    slug: str
    name: str
    source_url: str
    parser: ParserType
    category: AppCategory
    logo_src: str
    subtitle: str | None = None
    github_repo: str | None = None
    highlight_limit: int = HIGHLIGHT_LIMIT
    highlight_terms: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        if self.subtitle:
            return f"{self.name} ({self.subtitle})"
        return self.name

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS[self.category]


def _parser_from_yaml(slug: str, raw: object) -> ParserType:
    if raw not in _PARSER_NAMES:
        raise ValueError(
            f"App '{slug}': parser must be one of {', '.join(sorted(_PARSER_NAMES))}, got '{raw}'"
        )
    parser: ParserType = raw
    return parser


def _category_from_yaml(slug: str, raw: object) -> AppCategory:
    if raw not in CATEGORY_LABELS:
        raise ValueError(
            f"App '{slug}': category must be one of {', '.join(CATEGORY_LABELS)}, got '{raw}'"
        )
    category: AppCategory = raw
    return category


@lru_cache
def load_apps() -> tuple[AppConfig, ...]:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    apps: list[AppConfig] = []
    for item in raw.get("apps", []):
        slug = item["slug"]
        parser = _parser_from_yaml(slug, item["parser"])
        github_repo = item.get("github_repo")
        source_url = item.get("source_url")

        if parser in GITHUB_PARSERS:
            if not github_repo:
                raise ValueError(f"App '{slug}': {parser} requires github_repo")
            if not source_url:
                source_url = f"https://github.com/{github_repo.strip('/')}/releases"
        elif not source_url:
            raise ValueError(f"App '{slug}': source_url is required")

        terms = item.get("highlight_terms") or []
        apps.append(
            AppConfig(
                slug=slug,
                name=item["name"],
                source_url=source_url,
                parser=parser,
                category=_category_from_yaml(slug, item.get("category", "utilities")),
                logo_src=resolve_logo_src(slug, item.get("logo_url")),
                subtitle=item.get("subtitle"),
                github_repo=github_repo,
                highlight_limit=int(item.get("highlight_limit", HIGHLIGHT_LIMIT)),
                highlight_terms=tuple(str(term) for term in terms),
            )
        )
    return tuple(apps)


@lru_cache
def apps_by_slug() -> dict[str, AppConfig]:
    return {app.slug: app for app in load_apps()}


def all_slugs() -> list[str]:
    return [app.slug for app in load_apps()]


def apps_sorted_by_last_update(
    last_updates: dict[str, datetime] | None = None,
) -> tuple[AppConfig, ...]:
    updates = last_updates or {}
    return tuple(
        sorted(
            load_apps(),
            key=lambda app: (
                -(updates[app.slug].timestamp()) if app.slug in updates else float("inf"),
                app.slug,
            ),
        )
    )
