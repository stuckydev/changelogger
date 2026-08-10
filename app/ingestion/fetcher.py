from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.catalog.apps import AppConfig
from app.ingestion.errors import FetchError
from app.infra.http import get_http_client
from app.utils.date_utils import parse_datetime, parse_datetime_or_now


@dataclass(frozen=True)
class GitHubReleaseDraft:
    tag_name: str
    title: str
    body: str
    html_url: str
    published_at: datetime
    external_id: str


async def fetch_source(app: AppConfig) -> str:
    client = await get_http_client()
    response = await client.get(app.source_url)
    if response.status_code >= 400:
        raise FetchError(app.slug, f"HTTP {response.status_code} for {app.source_url}")
    return response.text


async def fetch_github_releases(github_repo: str, *, per_page: int = 30) -> list[dict]:
    client = await get_http_client()
    response = await client.get(
        f"https://api.github.com/repos/{github_repo}/releases",
        params={"per_page": per_page},
        headers={"Accept": "application/vnd.github+json"},
    )
    if response.status_code >= 400:
        raise FetchError(
            github_repo,
            f"HTTP {response.status_code} for GitHub releases API ({github_repo})",
        )
    data = response.json()
    if not isinstance(data, list):
        return []
    return data


def draft_from_release(release: dict) -> GitHubReleaseDraft | None:
    if release.get("prerelease") or release.get("draft"):
        return None
    tag_name = (release.get("tag_name") or "").strip()
    html_url = (release.get("html_url") or "").strip()
    title = (release.get("name") or tag_name or "Release").strip()
    if not tag_name and not html_url:
        return None
    published = parse_datetime(release.get("published_at")) or parse_datetime_or_now(
        release.get("created_at")
    )
    external_id = str(release.get("id") or html_url or tag_name)
    return GitHubReleaseDraft(
        tag_name=tag_name,
        title=title,
        body=release.get("body") or "",
        html_url=html_url or f"https://github.com/releases/tag/{tag_name}",
        published_at=published,
        external_id=external_id,
    )
