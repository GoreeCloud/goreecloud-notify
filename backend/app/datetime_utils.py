from __future__ import annotations

from datetime import datetime, timezone


UTC = timezone.utc


def as_utc(value: datetime) -> datetime:
    """Return a datetime representing the same instant with an explicit UTC timezone.

    SQLite reloads SQLAlchemy DateTime values without timezone information. Those
    database-loaded naive values are treated as UTC because all application writes
    must be normalized to UTC before persistence.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def require_explicit_timezone_utc(value: datetime | None) -> datetime | None:
    """Require an explicit client timezone and normalize the represented instant to UTC."""
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include an explicit timezone offset")
    return value.astimezone(UTC)
