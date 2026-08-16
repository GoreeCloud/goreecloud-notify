from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from . import models as _models  # noqa: F401 - registers SQLAlchemy metadata
from .database import Base

BACKUP_FORMAT = "goreecloud-notify-sqlite-backup-v1"


@dataclass(frozen=True, slots=True)
class BackupVerification:
    sha256: str
    size_bytes: int
    alembic_revision: str
    table_count: int


@dataclass(frozen=True, slots=True)
class BackupManifest:
    format: str
    created_at: str
    sha256: str
    size_bytes: int
    alembic_revision: str
    table_count: int


def sqlite_database_path(database_url: str) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("GoreeCloud Notify backup tooling currently supports SQLite only")
    if not url.database or url.database == ":memory:":
        raise ValueError("a file-backed SQLite database is required for backup")

    path = Path(url.database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30.0)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_schema(connection: sqlite3.Connection) -> tuple[str, int]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        detail = integrity[0] if integrity else "no result"
        raise RuntimeError(f"SQLite integrity_check failed: {detail}")

    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError(
            f"SQLite foreign_key_check found {len(foreign_key_errors)} violation(s)"
        )

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    expected_tables = set(Base.metadata.tables) | {"alembic_version"}
    missing = sorted(expected_tables - tables)
    if missing:
        raise RuntimeError(
            "backup is missing required GoreeCloud Notify table(s): " + ", ".join(missing)
        )

    version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if version is None or not version[0]:
        raise RuntimeError("backup does not contain an Alembic schema revision")

    return str(version[0]), len(tables)


def verify_sqlite_backup(path: Path) -> BackupVerification:
    backup_path = path.resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(f"backup file does not exist: {backup_path}")

    with _readonly_connection(backup_path) as connection:
        alembic_revision, table_count = _validate_schema(connection)

    return BackupVerification(
        sha256=_sha256_file(backup_path),
        size_bytes=backup_path.stat().st_size,
        alembic_revision=alembic_revision,
        table_count=table_count,
    )


def _write_manifest(path: Path, manifest: BackupManifest) -> None:
    if path.exists():
        raise FileExistsError(f"manifest already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{uuid4().hex}.partial")
    try:
        partial.write_text(
            json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def create_sqlite_backup(
    database_url: str,
    destination: Path,
    *,
    manifest_path: Path | None = None,
) -> BackupManifest:
    source = sqlite_database_path(database_url)
    if not source.is_file():
        raise FileNotFoundError(f"source SQLite database does not exist: {source}")

    target = destination.resolve()
    if target == source:
        raise ValueError("backup destination must differ from the live SQLite database")
    if target.exists():
        raise FileExistsError(f"backup destination already exists: {target}")

    final_manifest_path = (
        manifest_path.resolve()
        if manifest_path is not None
        else Path(f"{target}.manifest.json")
    )
    if final_manifest_path.exists():
        raise FileExistsError(f"manifest already exists: {final_manifest_path}")

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.name}.{uuid4().hex}.partial")
    try:
        with _readonly_connection(source) as source_connection:
            with sqlite3.connect(partial, timeout=30.0) as backup_connection:
                source_connection.backup(backup_connection)
                backup_connection.commit()

        verification = verify_sqlite_backup(partial)
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)

    manifest = BackupManifest(
        format=BACKUP_FORMAT,
        created_at=datetime.now(UTC).isoformat(),
        sha256=verification.sha256,
        size_bytes=verification.size_bytes,
        alembic_revision=verification.alembic_revision,
        table_count=verification.table_count,
    )
    _write_manifest(final_manifest_path, manifest)
    return manifest


def revoke_restored_web_sessions(path: Path) -> int:
    database_path = path.resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"restored SQLite database does not exist: {database_path}")

    revoked_at = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    with sqlite3.connect(database_path, timeout=30.0) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "web_sessions" not in tables:
            raise RuntimeError("restored database does not contain web_sessions")
        cursor = connection.execute(
            "UPDATE web_sessions SET revoked_at=? WHERE revoked_at IS NULL",
            (revoked_at,),
        )
        connection.commit()
        return int(cursor.rowcount)


def _configured_database_url() -> str:
    from .config import settings

    return settings.database_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and validate GoreeCloud Notify SQLite recovery snapshots."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser(
        "create",
        help="Create a consistent SQLite snapshot with the Online Backup API.",
    )
    create.add_argument("--destination", required=True, type=Path)
    create.add_argument("--manifest", type=Path)
    create.add_argument("--database-url")

    verify = commands.add_parser("verify", help="Verify a recovery snapshot.")
    verify.add_argument("--backup", required=True, type=Path)

    revoke = commands.add_parser(
        "revoke-restored-sessions",
        help="Invalidate all web sessions in an alternate/restored database before use.",
    )
    revoke.add_argument("--database", required=True, type=Path)

    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "create":
        manifest = create_sqlite_backup(
            args.database_url or _configured_database_url(),
            args.destination,
            manifest_path=args.manifest,
        )
        print(json.dumps(asdict(manifest), sort_keys=True))
        return 0
    if args.command == "verify":
        verification = verify_sqlite_backup(args.backup)
        print(json.dumps(asdict(verification), sort_keys=True))
        return 0
    if args.command == "revoke-restored-sessions":
        count = revoke_restored_web_sessions(args.database)
        print(json.dumps({"revoked_web_sessions": count}, sort_keys=True))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
