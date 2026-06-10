from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.infra.http import close_http_client
from app.infra.logos import ensure_logo_thumbs
from app.ingestion.sync import sync_all
from app.presentation.routes import api, health, pages
from app.settings import REFRESH_INTERVAL_SECONDS, STATIC_DIR
from app.storage.db import SessionLocal, engine
from app.storage.migrations import run_migrations

logger = logging.getLogger(__name__)


async def _run_sync_loop() -> None:
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            results = await sync_all(db)
            logger.info(
                "Background sync finished: %d ok, %d failed",
                sum(v is None for v in results.values()),
                sum(v is not None for v in results.values()),
            )
        except Exception:
            logger.exception("Background sync failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations(engine)
    ensure_logo_thumbs()
    db = SessionLocal()
    try:
        results = await sync_all(db)
        logger.info(
            "Initial sync finished: %d ok, %d failed",
            sum(v is None for v in results.values()),
            sum(v is not None for v in results.values()),
        )
    finally:
        db.close()

    sync_task = asyncio.create_task(_run_sync_loop())
    try:
        yield
    finally:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
        await close_http_client()


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(title="Changelogger", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(health.router)
    app.include_router(pages.router)
    app.include_router(api.router)
    return app


app = create_app()
