#!/usr/bin/env python3
"""Post-migration account setup.

- Resets the admin account password to a temporary value and flags it for
  mandatory change on first login.
- Flags every doctor who has no full_name to set one on first login.

Run INSIDE the backend container after sqlite_to_postgres.py succeeds:

    sudo docker compose -f docker/docker-compose.v3.yaml --env-file backend/.env run --rm \\
        -v "$(pwd)/scripts:/app/scripts" \\
        backend \\
        python scripts/setup_accounts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent
_backend_dir = _repo_root / "backend"
sys.path.insert(0, str(_backend_dir if _backend_dir.is_dir() else _repo_root))

from sqlalchemy import text
from app.core.database import engine
from app.core.security import hash_password
import app.db.models  # noqa: F401

TEMP_PASSWORD = "admin123"


def main() -> None:
    new_hash = hash_password(TEMP_PASSWORD)

    with engine.begin() as conn:
        # 1. Reset admin password + force change on next login
        result = conn.execute(
            text("""
                UPDATE doctors
                SET password_hash        = :hash,
                    must_change_password = TRUE,
                    must_set_name        = TRUE
                WHERE username = 'admin'
                RETURNING uuid, username
            """),
            {"hash": new_hash},
        )
        row = result.fetchone()
        if row:
            print(f"  [ok] admin ({row[1]}) password reset → '{TEMP_PASSWORD}' "
                  "(must change on first login)")
        else:
            print("  [!] no account with username='admin' found — skipping password reset")

        # 2. Flag every doctor with no full_name to set one on first login
        result = conn.execute(
            text("""
                UPDATE doctors
                SET must_set_name = TRUE
                WHERE (full_name IS NULL OR full_name = '')
                  AND username != 'admin'
                RETURNING username
            """)
        )
        flagged = [r[0] for r in result.fetchall()]
        if flagged:
            print(f"  [ok] must_set_name = TRUE for: {', '.join(flagged)}")
        else:
            print("  [ok] all non-admin doctors already have a full_name")

    print("\nAccount setup complete.")


if __name__ == "__main__":
    main()
