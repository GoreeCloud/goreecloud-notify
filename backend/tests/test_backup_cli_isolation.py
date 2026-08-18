from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine

from app import models as _models  # noqa: F401 - registers SQLAlchemy metadata
from app.orm import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _build_minimal_valid_backup(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path}")
    try:
        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()

    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        connection.execute(
            "INSERT INTO alembic_version (version_num) VALUES (?)",
            ("0005_login_abuse_controls",),
        )
        connection.commit()


def test_verify_cli_does_not_initialize_configured_runtime_database(tmp_path: Path) -> None:
    backup = tmp_path / "restored-notify.db"
    _build_minimal_valid_backup(backup)

    env = os.environ.copy()
    env["GOREECLOUD_NOTIFY_DATABASE_URL"] = (
        "sqlite:////proc/goreecloud-notify-verifier-must-not-create/runtime.db"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.backup",
            "verify",
            "--backup",
            str(backup),
        ],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["alembic_revision"] == "0005_login_abuse_controls"
    assert payload["size_bytes"] == backup.stat().st_size
    assert len(payload["sha256"]) == 64
