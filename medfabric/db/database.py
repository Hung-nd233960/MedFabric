# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# /medfabric/db/database.py
import os
import sqlite3
import uuid
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


# This function is called every time a new connection is established
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def return_engine():
    # For SQLite, we can add connect_args for thread safety
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(DATABASE_URL, echo=True, connect_args=connect_args)
