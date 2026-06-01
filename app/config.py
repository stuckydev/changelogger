from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import yaml

from app.constants import CONFIG_PATH, ROOT_DIR

ParserType = Literal["rss", "todoist_html", "notion_html", "github_releases"]


def github_releases_url(github_repo: str) -> str:
    return f"https://github.com/{github_repo.strip('/')}/releases.atom"


@dataclass(frozen=True)
class AppConfig:
    slug: str
    name: str
    color: str
    source_url: str
    parser: ParserType
    subtitle: str | None = None
    github_repo: str | None = None
    logo_url: str | None = None

    @property
    def display_name(self) -> str:
        if self.subtitle:
            return f"{self.name} ({self.subtitle})"
        return self.name

    @property
    def logo_src(self) -> str:
        if self.logo_url:
            return self.logo_url
        logo_dir = ROOT_DIR / "app" / "static" / "logos"
        for extension in (".png", ".ico", ".webp", ".svg"):
            if (logo_dir / f"{self.slug}{extension}").exists():
                return f"/static/logos/{self.slug}{extension}"
        return f"/static/logos/{self.slug}.svg"


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

        apps.append(
            AppConfig(
                slug=item["slug"],
                name=item["name"],
                color=item.get("color", "#64748b"),
                source_url=source_url,
                parser=parser,
                subtitle=item.get("subtitle"),
                github_repo=github_repo,
                logo_url=item.get("logo_url"),
            )
        )
    return tuple(apps)


def get_app(slug: str) -> AppConfig | None:
    return next((app for app in load_apps() if app.slug == slug), None)


def all_slugs() -> list[str]:
    return [app.slug for app in load_apps()]
