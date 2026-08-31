from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .config import settings
from .orm import Base


def _ensure_sqlite_parent(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return

    raw_path = database_url.removeprefix(prefix)
    if raw_path == ":memory:":
        return

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def configure_sqlite_engine(built_engine: Engine) -> Engine:
    if built_engine.dialect.name == "sqlite":
        event.listen(built_engine, "connect", _enable_sqlite_foreign_keys)
    return built_engine


def build_engine(database_url: str) -> Engine:
    _ensure_sqlite_parent(database_url)
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    return configure_sqlite_engine(create_engine(database_url, connect_args=connect_args))


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def verify_schema() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    required_tables = set(Base.metadata.tables)
    missing_tables = sorted(required_tables - tables)
    if missing_tables:
        raise RuntimeError(
            "database schema is not initialized; run `alembic -c alembic.ini upgrade head` "
            f"(missing tables: {', '.join(missing_tables)})"
        )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "password_hash" not in user_columns:
        raise RuntimeError(
            "database schema is behind the authentication migration; "
            "run `alembic -c alembic.ini upgrade head`"
        )
    if "is_admin" not in user_columns:
        raise RuntimeError(
            "database schema is behind the administrator-authorization migration; "
            "run `alembic -c alembic.ini upgrade head`"
        )

    session_columns = {column["name"] for column in inspector.get_columns("web_sessions")}
    if "csrf_token" not in session_columns:
        raise RuntimeError(
            "database schema is behind the CSRF migration; "
            "run `alembic -c alembic.ini upgrade head`"
        )

    notification_columns = {column["name"] for column in inspector.get_columns("notifications")}
    if "idempotency_digest" not in notification_columns:
        raise RuntimeError(
            "database schema is behind the notification-idempotency migration; "
            "run `alembic -c alembic.ini upgrade head`"
        )
