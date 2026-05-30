"""MedFabric 3.0 — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.about import get_about, set_startup_time
from app.core.limiter import limiter
from sqlalchemy import text

from app.core.database import Base, engine
import app.db.models  # noqa: F401 — registers all models with Base.metadata
from app.routers import (
    about,
    admin,
    annotation_sessions,
    auth,
    bug_reports,
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


def _add_missing_columns() -> None:
    """Add new columns to existing tables without dropping data (create_all won't do this)."""
    migrations = [
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_payload TEXT",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_saved_at TIMESTAMPTZ",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS draft_deleted_at TIMESTAMPTZ",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS must_set_name BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS registration_source VARCHAR(64) NOT NULL DEFAULT 'admin_created'",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS auto_draft_payload TEXT",
        "ALTER TABLE annotation_sessions ADD COLUMN IF NOT EXISTS auto_draft_saved_at TIMESTAMPTZ",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE",
        "UPDATE doctors SET is_test = TRUE WHERE role = 'Admin' AND is_test = FALSE",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ",
        "ALTER TABLE doctors ADD COLUMN IF NOT EXISTS preferences JSONB",
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
    set_startup_time()
    get_about()  # load and cache about.toml; logs name/version/creator
    logger.info(
        "MedFabric %s starting up — creating tables if needed", settings.app_version
    )
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    yield
    logger.info("MedFabric shutting down")


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    docs_url="/api/docs" if settings.expose_api_docs else None,
    redoc_url="/api/redoc" if settings.expose_api_docs else None,
    openapi_url="/api/openapi.json" if settings.expose_api_docs else None,
    lifespan=lifespan,
)

# Rate limiter — 429 on exceeded limits
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers on every response
app.add_middleware(SecurityHeadersMiddleware)

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
    about,
    auth,
    bug_reports,
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
