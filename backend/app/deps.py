from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from .database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
