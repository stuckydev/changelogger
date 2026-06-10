from __future__ import annotations

import httpx

from app.core.constants import HTTP_TIMEOUT, USER_AGENT

_http_client: httpx.AsyncClient | None = None


def _default_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xml,text/xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers=_default_headers(),
        )
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
