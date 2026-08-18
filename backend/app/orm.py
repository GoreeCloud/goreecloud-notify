from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared GoreeCloud Notify SQLAlchemy metadata without runtime engine side effects."""

    pass
