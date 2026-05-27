#!/usr/bin/env python3
"""Migrate medfabric.db from v2 schema to v3.

Run from the repo root:
    python scripts/migrate_v2_to_v3.py [path/to/medfabric.db]

A backup is created at <db_path>.v2_backup before any changes are made.

Key changes applied:
  - sessions            → renamed to login_sessions
  - annotation_sessions → new table (synthesised from old evaluation rows)
  - image_set_evaluations → recreated: doctor_uuid + session_uuid replaced by
                             annotation_session_uuid; notes column added
  - image_evaluations   → recreated: same FK change; UNIQUE constraint updated
  - datasets            → is_active, created_at columns added
  - doctors             → is_active, is_test, full_name, must_change_password,
                           must_set_name, registration_source, created_at added
  - image_sets          → conflicted column dropped; is_active, created_at added
  - doctor_dataset_assignments, admin_audit_log → new empty tables
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import uuid as uuid_lib
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_DB = Path(__file__).resolve().parent.parent / "medfabric.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dict_rows(cursor: sqlite3.Cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def step_rename_sessions(conn: sqlite3.Connection) -> None:
    """Rename sessions → login_sessions."""
    conn.execute("ALTER TABLE sessions RENAME TO login_sessions")
    print("  [ok] sessions → login_sessions")


def step_add_columns(conn: sqlite3.Connection) -> None:
    """Add missing columns to datasets, doctors, image_sets.

    SQLite's ALTER TABLE ADD COLUMN requires a *constant* DEFAULT for NOT NULL
    columns — CURRENT_TIMESTAMP is not accepted.  We use a fixed sentinel
    timestamp for existing rows; new rows get the real value via the ORM default.
    """
    fallback_ts = "2000-01-01 00:00:00"
    stmts = [
        # datasets
        "ALTER TABLE datasets ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
        f"ALTER TABLE datasets ADD COLUMN created_at DATETIME NOT NULL DEFAULT '{fallback_ts}'",
        # doctors
        "ALTER TABLE doctors ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
        "ALTER TABLE doctors ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE doctors ADD COLUMN full_name VARCHAR(255)",
        "ALTER TABLE doctors ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE doctors ADD COLUMN must_set_name BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE doctors ADD COLUMN registration_source VARCHAR(64) NOT NULL DEFAULT 'admin_created'",
        f"ALTER TABLE doctors ADD COLUMN created_at DATETIME NOT NULL DEFAULT '{fallback_ts}'",
        # image_sets
        "ALTER TABLE image_sets ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
        f"ALTER TABLE image_sets ADD COLUMN created_at DATETIME NOT NULL DEFAULT '{fallback_ts}'",
    ]
    for s in stmts:
        conn.execute(s)
    print("  [ok] added columns to datasets / doctors / image_sets")


def step_drop_conflicted(conn: sqlite3.Connection) -> None:
    """Drop image_sets.conflicted (no longer in v3 model)."""
    conn.execute("ALTER TABLE image_sets DROP COLUMN conflicted")
    print("  [ok] dropped image_sets.conflicted")


def step_fix_doctor_roles(conn: sqlite3.Connection) -> None:
    """Fill NULL roles: 'admin' username → Admin, everyone else → Doctor."""
    conn.execute(
        "UPDATE doctors SET role = 'Admin' WHERE username = 'admin' AND (role IS NULL OR role = '')"
    )
    conn.execute(
        "UPDATE doctors SET role = 'Doctor' WHERE role IS NULL OR role = ''"
    )
    cur = conn.execute("SELECT COUNT(*) FROM doctors WHERE role IS NULL OR role = ''")
    remaining = cur.fetchone()[0]
    if remaining:
        raise RuntimeError(f"{remaining} doctors still have a NULL role after fix-up")
    print("  [ok] doctor roles resolved")


def step_create_annotation_sessions(conn: sqlite3.Connection) -> None:
    """Create the annotation_sessions table."""
    conn.execute("""
        CREATE TABLE annotation_sessions (
            annotation_session_uuid CHAR(36)  NOT NULL PRIMARY KEY,
            doctor_uuid             CHAR(36)  NOT NULL
                REFERENCES doctors(uuid),
            image_set_uuid          CHAR(36)  NOT NULL
                REFERENCES image_sets(uuid),
            login_session_uuid      CHAR(36)  NOT NULL
                REFERENCES login_sessions(session_uuid),
            started_at              DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at            DATETIME,
            draft_payload           TEXT,
            draft_saved_at          DATETIME,
            draft_deleted_at        DATETIME,
            auto_draft_payload      TEXT,
            auto_draft_saved_at     DATETIME
        )
    """)
    print("  [ok] created annotation_sessions table")


def step_populate_annotation_sessions(
    conn: sqlite3.Connection,
) -> dict[tuple[str, str, str], str]:
    """
    Synthesise one annotation_session for every unique
    (doctor_uuid, image_set_uuid, session_uuid) triplet found in the old
    evaluation rows.  Returns a mapping from that triplet to the new
    annotation_session_uuid.
    """
    # Collect triplets from image_set_evaluations
    cur = conn.execute(
        "SELECT DISTINCT doctor_uuid, image_set_uuid, session_uuid "
        "FROM image_set_evaluations"
    )
    triplets: set[tuple[str, str, str]] = {
        (r[0], r[1], r[2]) for r in cur.fetchall()
    }

    # Collect triplets from image_evaluations (image_set_uuid via images join)
    cur = conn.execute("""
        SELECT DISTINCT ie.doctor_uuid, img.image_set_uuid, ie.session_uuid
        FROM image_evaluations ie
        JOIN images img ON img.uuid = ie.image_uuid
    """)
    triplets |= {(r[0], r[1], r[2]) for r in cur.fetchall()}

    mapping: dict[tuple[str, str, str], str] = {}

    for doctor_uuid, image_set_uuid, session_uuid in sorted(triplets):
        annot_uuid = str(uuid_lib.uuid4())

        # Use the login_time of the original session as started_at / submitted_at
        cur2 = conn.execute(
            "SELECT login_time FROM login_sessions WHERE session_uuid = ?",
            (session_uuid,),
        )
        row = cur2.fetchone()
        ts = row[0] if row else now_iso()

        conn.execute(
            """INSERT INTO annotation_sessions
               (annotation_session_uuid, doctor_uuid, image_set_uuid,
                login_session_uuid, started_at, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (annot_uuid, doctor_uuid, image_set_uuid, session_uuid, ts, ts),
        )
        mapping[(doctor_uuid, image_set_uuid, session_uuid)] = annot_uuid

    print(f"  [ok] created {len(mapping)} annotation_session(s)")
    return mapping


def step_recreate_image_set_evaluations(
    conn: sqlite3.Connection,
    mapping: dict[tuple[str, str, str], str],
) -> None:
    """
    Recreate image_set_evaluations:
      - swap doctor_uuid + session_uuid → annotation_session_uuid
      - add notes column
    """
    old_rows = _dict_rows(
        conn.execute("SELECT * FROM image_set_evaluations")
    )

    conn.execute("DROP TABLE image_set_evaluations")

    conn.execute("""
        CREATE TABLE image_set_evaluations (
            id                      INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
            annotation_session_uuid CHAR(36) NOT NULL UNIQUE
                REFERENCES annotation_sessions(annotation_session_uuid),
            image_set_uuid          CHAR(36) NOT NULL
                REFERENCES image_sets(uuid),
            image_set_usability     VARCHAR(18) NOT NULL,
            ischemic_low_quality    BOOLEAN  NOT NULL,
            notes                   TEXT
        )
    """)

    for row in old_rows:
        key = (row["doctor_uuid"], row["image_set_uuid"], row["session_uuid"])
        annot_uuid = mapping[key]
        conn.execute(
            """INSERT INTO image_set_evaluations
               (annotation_session_uuid, image_set_uuid,
                image_set_usability, ischemic_low_quality, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (
                annot_uuid,
                row["image_set_uuid"],
                row["image_set_usability"],
                row["ischemic_low_quality"],
                row.get("notes"),
            ),
        )

    print(f"  [ok] recreated image_set_evaluations ({len(old_rows)} rows)")


def step_recreate_image_evaluations(
    conn: sqlite3.Connection,
    mapping: dict[tuple[str, str, str], str],
) -> None:
    """
    Recreate image_evaluations:
      - swap doctor_uuid + session_uuid → annotation_session_uuid
      - update UNIQUE constraint to (annotation_session_uuid, image_uuid)
    """
    score_cols = [
        "c_left_score", "c_right_score",
        "ic_left_score", "ic_right_score",
        "l_left_score", "l_right_score",
        "i_left_score", "i_right_score",
        "m1_left_score", "m1_right_score",
        "m2_left_score", "m2_right_score",
        "m3_left_score", "m3_right_score",
        "m4_left_score", "m4_right_score",
        "m5_left_score", "m5_right_score",
        "m6_left_score", "m6_right_score",
    ]

    # Fetch old rows, pulling image_set_uuid via images join
    old_rows = _dict_rows(conn.execute("""
        SELECT ie.*, img.image_set_uuid AS _image_set_uuid
        FROM image_evaluations ie
        JOIN images img ON img.uuid = ie.image_uuid
    """))

    conn.execute("DROP TABLE image_evaluations")

    score_col_defs = "\n".join(
        f"            {c} VARCHAR(17) NOT NULL," for c in score_cols
    )
    conn.execute(f"""
        CREATE TABLE image_evaluations (
            id                      INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
            annotation_session_uuid CHAR(36) NOT NULL
                REFERENCES annotation_sessions(annotation_session_uuid),
            image_uuid              CHAR(36) NOT NULL
                REFERENCES images(uuid),
            region                  VARCHAR(13) NOT NULL,
{score_col_defs}
            notes                   TEXT,
            UNIQUE (annotation_session_uuid, image_uuid)
        )
    """)

    score_placeholders = ", ".join("?" for _ in score_cols)
    score_col_names = ", ".join(score_cols)

    for row in old_rows:
        key = (row["doctor_uuid"], row["_image_set_uuid"], row["session_uuid"])
        annot_uuid = mapping[key]
        score_values = [row[c] for c in score_cols]
        conn.execute(
            f"""INSERT INTO image_evaluations
               (annotation_session_uuid, image_uuid, region,
                {score_col_names}, notes)
               VALUES (?, ?, ?, {score_placeholders}, ?)""",
            [annot_uuid, row["image_uuid"], row["region"], *score_values, row.get("notes")],
        )

    print(f"  [ok] recreated image_evaluations ({len(old_rows)} rows)")


def step_create_admin_tables(conn: sqlite3.Connection) -> None:
    """Create doctor_dataset_assignments and admin_audit_log."""
    conn.execute("""
        CREATE TABLE doctor_dataset_assignments (
            id           INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
            doctor_uuid  CHAR(36) NOT NULL REFERENCES doctors(uuid),
            dataset_uuid CHAR(36) NOT NULL REFERENCES datasets(dataset_uuid),
            assigned_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_active    BOOLEAN  NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE admin_audit_log (
            id           INTEGER      NOT NULL PRIMARY KEY AUTOINCREMENT,
            admin_uuid   CHAR(36)     NOT NULL REFERENCES doctors(uuid),
            action       VARCHAR(128) NOT NULL,
            target_table VARCHAR(128) NOT NULL,
            target_id    VARCHAR(255),
            detail       TEXT,
            timestamp    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  [ok] created doctor_dataset_assignments + admin_audit_log")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def migrate(db_path: Path) -> None:
    backup_path = db_path.with_suffix(".db.v2_backup")
    shutil.copy2(db_path, backup_path)
    print(f"Backup → {backup_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Disable FK enforcement while we restructure
        conn.execute("PRAGMA foreign_keys = OFF")

        with conn:  # single transaction — rolls back on any exception
            print("\nRunning migration steps:")
            step_rename_sessions(conn)
            step_add_columns(conn)
            step_fix_doctor_roles(conn)
            step_drop_conflicted(conn)
            step_create_annotation_sessions(conn)
            mapping = step_populate_annotation_sessions(conn)
            step_recreate_image_set_evaluations(conn, mapping)
            step_recreate_image_evaluations(conn, mapping)
            step_create_admin_tables(conn)

        conn.execute("PRAGMA foreign_keys = ON")
        # Quick sanity check
        conn.execute("PRAGMA integrity_check")
        print("\nMigration complete. Run integrity_check...")
        cur = conn.execute("PRAGMA integrity_check")
        result = cur.fetchone()[0]
        print(f"  integrity_check: {result}")

    except Exception:
        print("\nMigration FAILED — database restored from backup is unchanged.")
        conn.close()
        raise

    finally:
        conn.close()

    print(
        "\nNext steps:\n"
        "  1. cd backend\n"
        "  2. Generate your initial Alembic migration (or stamp if already done):\n"
        "       alembic revision --autogenerate -m 'v3_initial'\n"
        "       alembic stamp head\n"
        "  3. Verify with:  alembic current\n"
    )


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    if not path.exists():
        sys.exit(f"Error: database not found at {path}")
    migrate(path)
