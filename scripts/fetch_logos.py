"""One-off helper to download official app logos into app/static/logos/."""
from __future__ import annotations

from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = ROOT / "app" / "static" / "logos"
HEADERS = {"User-Agent": "Changelogger/1.0 (+https://github.com/changelogger)"}

SOURCES = {
    "todoist": {
        "url": "https://www.todoist.com/static/apple-touch-icon.png",
        "filename": "todoist.png",
        "source_note": "todoist.com apple-touch-icon",
    },
    "1password": {
        "url": "https://1password.com/apple-touch-icon.png",
        "filename": "1password.png",
        "source_note": "1password.com apple-touch-icon",
    },
    "notion": {
        "url": "https://www.notion.com/front-static/logo-ios.png",
        "filename": "notion.png",
        "source_note": "notion.com official logo-ios",
    },
    "actual": {
        "url": "https://raw.githubusercontent.com/actualbudget/actual/master/packages/desktop-client/public/favicon.ico",
        "filename": "actual.ico",
        "source_note": "actualbudget/actual official app favicon",
    },
    "winutil": {
        "url": "https://github.com/ChrisTitusTech.png",
        "filename": "winutil.png",
        "source_note": "ChrisTitusTech GitHub organization avatar",
    },
    "capacities": {
        "url": "https://capacities.io/favicon.ico",
        "filename": "capacities.ico",
        "source_note": "capacities.io favicon",
    },
}


def main() -> None:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
        for slug, meta in SOURCES.items():
            response = client.get(meta["url"])
            response.raise_for_status()
            target = LOGO_DIR / meta["filename"]
            target.write_bytes(response.content)
            print(f"OK {slug}: {len(response.content)} bytes -> {target.name} ({meta['source_note']})")


if __name__ == "__main__":
    main()
