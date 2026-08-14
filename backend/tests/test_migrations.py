from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, bindparam, create_engine, inspect, text


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
    assert "csrf_token" in {column["name"] for column in inspector.get_columns("web_sessions")}


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
    assert "csrf_token" in {column["name"] for column in after.get_columns("web_sessions")}


def test_csrf_migration_revokes_existing_human_sessions(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'csrf-upgrade.db'}"
    run_alembic(database_url, "0002_human_authentication")

    engine = create_engine(database_url)
    datetime_type = DateTime(timezone=True)
    insert_user = text(
        "INSERT INTO users (username, display_name, password_hash, is_active, created_at) "
        "VALUES (:username, :display_name, :password_hash, :is_active, :created_at)"
    ).bindparams(bindparam("created_at", type_=datetime_type))
    insert_session = text(
        "INSERT INTO web_sessions "
        "(user_id, session_digest, created_at, last_seen_at, expires_at, revoked_at) "
        "VALUES (:user_id, :session_digest, :created_at, :last_seen_at, :expires_at, NULL)"
    ).bindparams(
        bindparam("created_at", type_=datetime_type),
        bindparam("last_seen_at", type_=datetime_type),
        bindparam("expires_at", type_=datetime_type),
    )
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            insert_user,
            {
                "username": "existing",
                "display_name": "Existing User",
                "password_hash": "$argon2id$placeholder",
                "is_active": True,
                "created_at": now,
            },
        )
        user_id = connection.execute(text("SELECT id FROM users WHERE username='existing'")).scalar_one()
        connection.execute(
            insert_session,
            {
                "user_id": user_id,
                "session_digest": "a" * 64,
                "created_at": now,
                "last_seen_at": now,
                "expires_at": now + timedelta(hours=1),
            },
        )
    engine.dispose()

    run_alembic(database_url, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT csrf_token, revoked_at FROM web_sessions WHERE session_digest=:digest"),
            {"digest": "a" * 64},
        ).one()
        assert row.csrf_token
        assert row.revoked_at is not None
