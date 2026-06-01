from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.constants import REFRESH_INTERVAL_SECONDS, ROOT_DIR
from app.db import SessionLocal, engine
from app.migrations import run_migrations
from app.routers import api, pages
from app.services.sync import sync_all

logger = logging.getLogger(__name__)


async def _run_sync_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            results = await sync_all(db)
            app.state.sync_errors = {
                slug: message for slug, message in results.items() if isinstance(message, str)
            }
            logger.info("Background sync finished: %s", results)
        except Exception:
            logger.exception("Background sync failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(engine)
    app.state.sync_errors = {}
    db = SessionLocal()
    try:
        results = await sync_all(db)
        app.state.sync_errors = {
            slug: message for slug, message in results.items() if isinstance(message, str)
        }
        logger.info("Initial sync finished: %s", results)
    finally:
        db.close()

    sync_task = asyncio.create_task(_run_sync_loop(app))
    try:
        yield
    finally:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(title="Changelogger", lifespan=lifespan)
    static_dir = ROOT_DIR / "app" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(pages.router)
    app.include_router(api.router)
    return app


app = create_app()
