from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.infra.http import close_http_client
from app.infra.logos import ensure_logo_thumbs
from app.ingestion.sync import sync_all
from app.presentation.routes import api, health, pages
from app.settings import STATIC_DIR
from app.storage.db import SessionLocal, engine
from app.storage.migrations import run_migrations
from app.utils.date_utils import seconds_until_next_hour

logger = logging.getLogger(__name__)


async def _sync_once(label: str) -> None:
    db = SessionLocal()
    try:
        results = await sync_all(db)
        logger.info(
            "%s finished: %d ok, %d failed",
            label,
            sum(v is None for v in results.values()),
            sum(v is not None for v in results.values()),
        )
    except Exception:
        logger.exception("%s failed", label)
    finally:
        db.close()


async def _run_sync_loop() -> None:
    while True:
        await asyncio.sleep(seconds_until_next_hour())
        await _sync_once("Background sync")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Changelogger started")
    run_migrations(engine)
    ensure_logo_thumbs()

    # Serve immediately; first sync fills the cache in the background.
    initial_sync_task = asyncio.create_task(_sync_once("Initial sync"))
    sync_task = asyncio.create_task(_run_sync_loop())
    try:
        yield
    finally:
        for task in (initial_sync_task, sync_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await close_http_client()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )

    app = FastAPI(title="Changelogger", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(health.router)
    app.include_router(pages.router)
    app.include_router(api.router)
    return app


app = create_app()
