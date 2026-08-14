from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect


def run_alembic(database_url: str, revision: str) -> None:
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


def test_fresh_database_reaches_authentication_head(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    run_alembic(database_url, "head")

    inspector = inspect(create_engine(database_url))
    assert "web_sessions" in inspector.get_table_names()
    assert "password_hash" in {column["name"] for column in inspector.get_columns("users")}


def test_existing_baseline_database_upgrades_without_recreation(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    run_alembic(database_url, "0001_milestone_2_baseline")

    engine = create_engine(database_url)
    before = inspect(engine)
    assert "web_sessions" not in before.get_table_names()
    assert "password_hash" not in {column["name"] for column in before.get_columns("users")}
    engine.dispose()

    run_alembic(database_url, "head")
    after = inspect(create_engine(database_url))
    assert "web_sessions" in after.get_table_names()
    assert "password_hash" in {column["name"] for column in after.get_columns("users")}
