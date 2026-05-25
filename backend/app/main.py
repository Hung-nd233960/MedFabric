"""MedFabric 3.0 — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from sqlalchemy import text

from app.core.database import Base, engine
import app.db.models  # noqa: F401 — registers all models with Base.metadata
from app.routers import (
    admin,
    annotation_sessions,
    auth,
    dashboard,
    datasets,
    evaluations,
    export,
    image_sets,
    images,
    patients,
)

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _add_missing_columns() -> None:
    """Add new columns to existing tables without dropping data (create_all won't do this)."""
    migrations = [
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_payload TEXT",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_saved_at TIMESTAMPTZ",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_deleted_at TIMESTAMPTZ",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS registration_source VARCHAR(64) NOT NULL DEFAULT 'admin_created'",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception as exc:  # pragma: no cover
                logger.warning("Column migration skipped: %s", exc)
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MedFabric %s starting up — creating tables if needed", settings.app_version)
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    yield
    logger.info("MedFabric shutting down")


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS — allow the React dev server; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api
API_PREFIX = "/api"
for router_module in [
    auth,
    datasets,
    patients,
    image_sets,
    images,
    annotation_sessions,
    evaluations,
    dashboard,
    admin,
    export,
]:
    app.include_router(router_module.router, prefix=API_PREFIX)
