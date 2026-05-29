"""Public endpoints — software information from about.toml and runtime diagnostics."""

import re
import sys
from datetime import datetime, timezone

import fastapi
import sqlalchemy
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.about import AboutInfo, get_about, get_startup_time
from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(prefix="/about", tags=["about"])


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
