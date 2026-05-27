#!/usr/bin/env python3
"""Transfer data from a v3-migrated SQLite file into the PostgreSQL database.

Intended to run INSIDE the backend Docker container (DATABASE_URL is set there):

    docker compose -f docker/docker-compose.v3.yaml --env-file backend/.env run --rm \\
        -v $(pwd)/medfabric.db:/tmp/medfabric.db \\
        backend \\
        python scripts/sqlite_to_postgres.py /tmp/medfabric.db

Pre-conditions:
  • The SQLite file must already be at v3 schema (run migrate_v2_to_v3.py first).
  • The PostgreSQL container must be running and reachable via DATABASE_URL.
  • The PostgreSQL database must be empty (or the tables must not exist yet).

The script creates all tables in Postgres via SQLAlchemy then copies every row
in FK-safe insertion order.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Resolve the directory that contains the `app/` package.
# • Host  : <repo>/backend/app  → insert <repo>/backend
# • Docker: /app/app            → insert /app  (no "backend" subfolder)
_repo_root = Path(__file__).resolve().parent.parent
_backend_dir = _repo_root / "backend"
sys.path.insert(0, str(_backend_dir if _backend_dir.is_dir() else _repo_root))

from sqlalchemy import Boolean, text

# These imports trigger model registration with Base.metadata
from app.core.database import Base, engine  # noqa: E402
import app.db.models  # noqa: F401, E402


# ---------------------------------------------------------------------------
# Build a set of (table, column) pairs whose Postgres type is BOOLEAN so we
# can cast SQLite's 0/1 integers to Python bool before inserting.
# ---------------------------------------------------------------------------
def _boolean_columns() -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, Boolean):
                result.add((table.name, col.name))
    return result


BOOL_COLS: set[tuple[str, str]] = _boolean_columns()


# ---------------------------------------------------------------------------
# FK-safe insertion order
# ---------------------------------------------------------------------------
TABLES = [
    "datasets",
    "doctors",
    "patients",
    "image_sets",
    "images",
    "login_sessions",
    "annotation_sessions",
    "image_set_evaluations",
    "image_evaluations",
    "doctor_dataset_assignments",
    "admin_audit_log",
]


def _sqlite_rows(sqlite_path: str, table: str) -> tuple[list[str], list[tuple]]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(f'SELECT * FROM "{table}"')
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if rows else []
    if not cols and not rows:
        # table may be empty — get column names from pragma
        cur2 = conn.execute(f'PRAGMA table_info("{table}")')
        cols = [r[1] for r in cur2.fetchall()]
    result = [tuple(r) for r in rows]
    conn.close()
    return cols, result


def _pg_table_exists(pg_conn, table: str) -> bool:
    row = pg_conn.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:t"
        ),
        {"t": table},
    ).fetchone()
    return row is not None


def _pg_row_count(pg_conn, table: str) -> int:
    row = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).fetchone()
    return row[0] if row else 0


def transfer(sqlite_path: str) -> None:
    print(f"Source SQLite : {sqlite_path}")
    print(f"Target Postgres: {engine.url}\n")

    # 1. Create schema in Postgres
    print("Creating tables in Postgres (if not exist)...")
    Base.metadata.create_all(bind=engine)
    print("  [ok] schema ready\n")

    with engine.begin() as pg_conn:
        # Safety guard — abort if any table already has rows
        non_empty = [
            t for t in TABLES
            if _pg_table_exists(pg_conn, t) and _pg_row_count(pg_conn, t) > 0
        ]
        if non_empty:
            print(
                "ERROR: The following Postgres tables already contain data:\n"
                + "\n".join(f"  {t}" for t in non_empty)
                + "\nAborting to prevent duplicates. "
                  "Truncate them first or use a fresh database."
            )
            sys.exit(1)

        # Disable FK checks during bulk load (Postgres syntax)
        pg_conn.execute(text("SET session_replication_role = 'replica'"))

        for table in TABLES:
            cols, rows = _sqlite_rows(sqlite_path, table)

            if not rows:
                print(f"  {table}: 0 rows (skipped)")
                continue

            # Build parameterised INSERT
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            stmt = text(
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'
            )

            batch = []
            for row in rows:
                record = dict(zip(cols, row))
                # Coerce SQLite 0/1 integers to Python bool for Postgres BOOLEAN cols
                for col in cols:
                    if (table, col) in BOOL_COLS and isinstance(record[col], int):
                        record[col] = bool(record[col])
                # Fix NULL doctor roles: admin username → Admin, everyone else → Doctor
                if table == "doctors" and not record.get("role"):
                    record["role"] = (
                        "Admin" if record.get("username") == "admin" else "Doctor"
                    )
                batch.append(record)
            pg_conn.execute(stmt, batch)
            print(f"  {table}: {len(rows)} rows inserted")

        # Re-enable FK checks
        pg_conn.execute(text("SET session_replication_role = 'origin'"))

    print("\nTransfer complete.")
    print(
        "\nNext steps:\n"
        "  docker compose -f docker/docker-compose.v3.yaml "
        "--env-file backend/.env up -d"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python sqlite_to_postgres.py <path/to/medfabric.db>")
    transfer(sys.argv[1])
