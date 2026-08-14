from app.database import Base
from app import models  # noqa: F401


def test_milestone_1_defines_all_planned_first_class_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "devices",
        "service_identities",
        "sources",
        "channels",
        "subscriptions",
        "notifications",
        "deliveries",
        "access_tokens",
        "preferences",
    }
