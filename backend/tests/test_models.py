from app import models  # noqa: F401
from app.database import Base


def test_milestone_2_keeps_planned_tables_plus_security_state() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "web_sessions",
        "admin_audit_events",
        "login_rate_buckets",
        "login_security_events",
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
