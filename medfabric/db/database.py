# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# /medfabric/db/database.py
import logging
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


load_dotenv()

# Ensure SQLite can bind uuid.UUID objects when TypeDecorators are bypassed
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

# Use SQLite - stores in a local file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medfabric.db")


def _sqlite_db_path(database_url: str) -> Path | None:
    """Return filesystem path for sqlite:/// URLs, else None."""
    if not database_url.startswith("sqlite:///"):
        return None
    raw_path = database_url.removeprefix("sqlite:///")
    return Path(raw_path).resolve()


def _cleanup_sqlite_sidecar_dirs(database_url: str) -> None:
    """Remove malformed SQLite sidecar directories if they exist."""
    db_path = _sqlite_db_path(database_url)
    if db_path is None:
        return

    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.is_dir():
            logging.warning(
                "Removing malformed SQLite sidecar directory: %s", sidecar
            )
            shutil.rmtree(sidecar, ignore_errors=True)


_cleanup_sqlite_sidecar_dirs(DATABASE_URL)


# This function is called every time a new connection is established
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        except sqlite3.OperationalError:
            logging.warning("Could not enable SQLite foreign keys pragma.", exc_info=True)

        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # Some filesystems or stale lock artifacts can make WAL unusable.
            # Fall back to default journaling mode instead of crashing startup.
            logging.warning(
                "Could not enable SQLite WAL mode; falling back to DELETE journal mode.",
                exc_info=True,
            )
            try:
                cursor.execute("PRAGMA journal_mode=DELETE")
            except sqlite3.OperationalError:
                logging.warning(
                    "Could not set SQLite DELETE journal mode. Using SQLite default.",
                    exc_info=True,
                )
        cursor.close()


def return_engine():
    # For SQLite, we can add connect_args for thread safety
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 30}

    return create_engine(DATABASE_URL, echo=True, connect_args=connect_args)
