from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from app.constants import HTTP_TIMEOUT, USER_AGENT

PR_LINE_RE = re.compile(r"^#\d+")
BLOG_PATH_RE = re.compile(r"actualbudget\.org/blog/release-", re.I)


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def parse_actual_blog(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    heading = main.find("h1")
    page_title = heading.get_text(" ", strip=True) if heading else ""

    lines: list[str] = []
    for li in main.find_all("li"):
        text = li.get_text(" ", strip=True)
        if not text or PR_LINE_RE.match(text):
            continue
        if len(text) < 18:
            continue
        lines.append(text)

    return page_title, lines


def enrich_from_detail_url(detail_url: str) -> tuple[str, list[str]]:
    if not detail_url:
        return "", []

    if BLOG_PATH_RE.search(detail_url):
        if not detail_url.endswith("/"):
            detail_url = detail_url.rstrip("/") + "/"
        html = fetch_html(detail_url)
        return parse_actual_blog(html)

    return "", []


def pick_display_title(version_title: str, page_title: str, highlights: list[str]) -> str:
    if page_title:
        return page_title
    if highlights and not _is_version_only(version_title):
        return version_title
    if highlights:
        first = highlights[0]
        if len(first) <= 72:
            return first
    return version_title


def _is_version_only(title: str) -> bool:
    cleaned = title.strip().lower()
    return bool(re.fullmatch(r"v?[\d.]+", cleaned) or re.fullmatch(r"release\s+v?[\d.]+", cleaned))
