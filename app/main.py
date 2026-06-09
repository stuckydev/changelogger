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
from app.services.fetch import close_http_client
from app.services.logo_thumbs import ensure_logo_thumbs
from app.services.sync import sync_all

logger = logging.getLogger(__name__)


def _sync_errors(results: dict[str, str | None]) -> dict[str, str]:
    return {slug: message for slug, message in results.items() if message}


async def _run_sync_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            results = await sync_all(db)
            app.state.sync_errors = _sync_errors(results)
            logger.info("Background sync finished: %d ok, %d failed", sum(v is None for v in results.values()), len(app.state.sync_errors))
        except Exception:
            logger.exception("Background sync failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(engine)
    ensure_logo_thumbs()
    app.state.sync_errors = {}
    db = SessionLocal()
    try:
        results = await sync_all(db)
        app.state.sync_errors = _sync_errors(results)
        logger.info("Initial sync finished: %d ok, %d failed", sum(v is None for v in results.values()), len(app.state.sync_errors))
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
        await close_http_client()


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(title="Changelogger", lifespan=lifespan)
    static_dir = ROOT_DIR / "app" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(pages.router)
    app.include_router(api.router)
    return app


app = create_app()
