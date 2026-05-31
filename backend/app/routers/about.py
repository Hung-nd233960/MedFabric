"""Public endpoints — software information, runtime diagnostics, and health check."""

import re
import sys
from datetime import datetime, timezone

import fastapi
import sqlalchemy
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.about import AboutInfo, get_about, get_startup_time
from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(prefix="/about", tags=["about"])


@router.get("/health", tags=["health"])
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    """Liveness + readiness probe. No authentication required.

    Returns 200 {"status": "ok"} when the app and database are reachable.
    Returns 503 {"status": "degraded", "detail": "..."} on DB failure.
    Intended for Uptime Kuma / load-balancer health checks.
    """
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError as exc:
        db_ok = False
        db_error = str(exc)

    if not db_ok:
        response.status_code = 503
        return {"status": "degraded", "detail": db_error}

    version = get_about().get("version", "unknown")
    return {"status": "ok", "version": version}


@router.get("", response_model=None)
def about() -> AboutInfo:
    """Return the contents of about.toml. No authentication required."""
    return get_about()


@router.get("/dev", response_model=None)
def about_dev(db: Session = Depends(get_db)) -> dict:
    """Return runtime diagnostic info. No authentication required."""
    settings = get_settings()

    # PostgreSQL version
    try:
        pg_raw: str = db.execute(text("SELECT version()")).scalar() or ""
        m = re.search(r"PostgreSQL (\S+)", pg_raw)
        pg_version = m.group(1) if m else pg_raw.split()[0]
    except Exception:
        pg_version = "unavailable"

    # Uptime
    startup = get_startup_time()
    now = datetime.now(timezone.utc)
    uptime_seconds = int((now - startup).total_seconds()) if startup else None

    return {
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
        "sqlalchemy_version": sqlalchemy.__version__,
        "postgres_version": pg_version,
        "startup_time": startup.isoformat() if startup else None,
        "uptime_seconds": uptime_seconds,
        "docker_version": settings.docker_version or None,
    }
