from __future__ import annotations

from datetime import datetime

from app.catalog.apps import AppConfig
from app.utils.date_utils import parse_datetime
from app.ingestion.errors import FetchError
from app.infra.http import get_http_client


async def fetch_source(app: AppConfig) -> str:
    client = await get_http_client()
    response = await client.get(app.source_url)
    if response.status_code >= 400:
        raise FetchError(app.slug, f"HTTP {response.status_code} for {app.source_url}")
    return response.text


async def fetch_github_release_dates(github_repo: str) -> dict[str, datetime]:
    from app.ingestion.parsers.github_releases import tag_lookup_keys

    client = await get_http_client()
    response = await client.get(
        f"https://api.github.com/repos/{github_repo}/releases",
        params={"per_page": 30},
        headers={"Accept": "application/vnd.github+json"},
    )
    if response.status_code >= 400:
        return {}

    dates: dict[str, datetime] = {}
    for release in response.json():
        tag_name = (release.get("tag_name") or "").strip()
        published = parse_datetime(release.get("published_at"))
        if not tag_name or published is None:
            continue
        for key in tag_lookup_keys(tag_name):
            dates[key] = published
    return dates
