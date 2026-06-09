from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import yaml

from app.constants import CONFIG_PATH, ROOT_DIR
from app.services.logo_thumbs import thumb_url_for_slug

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
    logo_dir = ROOT_DIR / "app" / "static" / "logos"
    for extension in (".png", ".ico", ".webp", ".svg"):
        path = logo_dir / f"{slug}{extension}"
        if path.exists():
            if extension != ".svg":
                thumb = thumb_url_for_slug(slug)
                if thumb:
                    return thumb
            return f"/static/logos/{slug}{extension}"
    return f"/static/logos/{slug}.svg"


@dataclass(frozen=True)
class AppConfig:
    slug: str
    name: str
    color: str
    source_url: str
    parser: ParserType
    logo_src: str
    subtitle: str | None = None
    github_repo: str | None = None
    logo_url: str | None = None
    github_simple: bool = False

    @property
    def display_name(self) -> str:
        if self.subtitle:
            return f"{self.name} ({self.subtitle})"
        return self.name


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

        slug = item["slug"]
        apps.append(
            AppConfig(
                slug=slug,
                name=item["name"],
                color=item.get("color", "#64748b"),
                source_url=source_url,
                parser=parser,
                logo_src=_resolve_logo_src(slug, item.get("logo_url")),
                subtitle=item.get("subtitle"),
                github_repo=github_repo,
                logo_url=item.get("logo_url"),
                github_simple=bool(item.get("github_simple")),
            )
        )
    apps.sort(key=lambda app: (app.display_name.casefold(), app.slug))
    return tuple(apps)


@lru_cache
def apps_by_slug() -> dict[str, AppConfig]:
    return {app.slug: app for app in load_apps()}


def get_app(slug: str) -> AppConfig | None:
    return apps_by_slug().get(slug)


def all_slugs() -> list[str]:
    return [app.slug for app in load_apps()]
