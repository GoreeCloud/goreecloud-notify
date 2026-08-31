from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect


def _upgrade(database_url: str, revision: str = "head") -> None:
    env = os.environ.copy()
    env["GOREECLOUD_NOTIFY_DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_idempotency_migration_is_sqlite_portable_and_source_scoped(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'idempotency.db'}"
    _upgrade(database_url, "0005_login_abuse_controls")

    before = inspect(create_engine(database_url))
    assert "idempotency_digest" not in {
        column["name"] for column in before.get_columns("notifications")
    }

    _upgrade(database_url)
    after = inspect(create_engine(database_url))
    assert "idempotency_digest" in {
        column["name"] for column in after.get_columns("notifications")
    }

    constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in after.get_unique_constraints("notifications")
    }
    assert constraints["uq_notification_source_idempotency"] == (
        "source_id",
        "idempotency_digest",
    )
