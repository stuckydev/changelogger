"""One-off helper to download official app logos into app/static/logos/."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.logo_thumbs import ensure_thumb
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
    "cursor": {
        "url": "https://cursor.com/apple-touch-icon.png",
        "filename": "cursor.png",
        "source_note": "cursor.com apple-touch-icon",
    },
    "workinghours": {
        "url": "https://store-images.s-microsoft.com/image/apps.5651.13799954966451185.8b83ae7c-0e20-4c14-9eb6-0a19cb73a11c.91d4fcdc-942c-43d5-8538-dafe9886ed52",
        "filename": "workinghours.png",
        "source_note": "Microsoft Store WorkingHours icon",
    },
    "glazewm": {
        "url": "https://github.com/glzr-io.png",
        "filename": "glazewm.png",
        "source_note": "glzr-io GitHub organization avatar",
    },
    "mtgarena": {
        "url": "https://cdn.cloudflare.steamstatic.com/steam/apps/2141910/logo.png",
        "filename": "mtgarena.png",
        "source_note": "Steam MTG Arena logo",
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
            thumb = ensure_thumb(target, slug)
            thumb_note = f", thumb {thumb.stat().st_size} bytes" if thumb else ""
            print(
                f"OK {slug}: {len(response.content)} bytes -> {target.name}{thumb_note} "
                f"({meta['source_note']})"
            )


if __name__ == "__main__":
    main()
