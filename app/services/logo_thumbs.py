from __future__ import annotations

import logging
from pathlib import Path

from app.constants import ROOT_DIR

logger = logging.getLogger(__name__)

LOGO_DIR = ROOT_DIR / "app" / "static" / "logos"
THUMB_SIZE = 48
RASTER_EXTENSIONS = {".png", ".ico", ".webp", ".jpg", ".jpeg", ".gif"}


def thumb_path_for_slug(slug: str) -> Path:
    return LOGO_DIR / "thumbs" / f"{slug}.webp"


def thumb_url_for_slug(slug: str) -> str | None:
    path = thumb_path_for_slug(slug)
    if path.exists():
        return f"/static/logos/thumbs/{slug}.webp"
    return None


def _write_thumb(source: Path, target: Path) -> None:
    from PIL import Image

    with Image.open(source) as image:
        image = image.convert("RGBA")
        image.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format="WEBP", quality=82, method=4)


def ensure_thumb(source: Path, slug: str) -> Path | None:
    if source.suffix.lower() not in RASTER_EXTENSIONS:
        return None

    target = thumb_path_for_slug(slug)
    try:
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            return target
        _write_thumb(source, target)
        return target
    except Exception:
        logger.exception("Could not create logo thumbnail for %s", slug)
        return None


def ensure_logo_thumbs() -> None:
    if not LOGO_DIR.is_dir():
        return

    for source in sorted(LOGO_DIR.iterdir()):
        if not source.is_file():
            continue
        if source.suffix.lower() not in RASTER_EXTENSIONS:
            continue
        ensure_thumb(source, source.stem)
