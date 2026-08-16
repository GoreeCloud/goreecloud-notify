from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import Base, build_engine
from app.models import Subscription


def test_sqlite_engine_enables_foreign_keys() -> None:
    test_engine = build_engine("sqlite:///:memory:")
    try:
        with test_engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    finally:
        test_engine.dispose()


def test_sqlite_rejects_orphan_foreign_key_insert() -> None:
    test_engine = build_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(bind=test_engine)

        with pytest.raises(IntegrityError):
            with test_engine.begin() as connection:
                connection.execute(
                    Subscription.__table__.insert().values(
                        user_id=999_001,
                        channel_id=999_002,
                        enabled=True,
                    )
                )
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
