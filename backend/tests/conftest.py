from __future__ import annotations

import pytest

from app.database import Base, engine


@pytest.fixture(autouse=True)
def isolated_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
