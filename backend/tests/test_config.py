from __future__ import annotations

import pytest

from app.config import Settings, _env_bool


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        (" on ", True),
        ("0", False),
        ("false", False),
        ("NO", False),
        (" off ", False),
    ],
)
def test_env_bool_accepts_explicit_true_and_false_values(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: bool,
) -> None:
    monkeypatch.setenv("GOREECLOUD_NOTIFY_TEST_BOOL", raw)

    assert _env_bool("GOREECLOUD_NOTIFY_TEST_BOOL", default=not expected) is expected


def test_env_bool_uses_default_when_variable_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOREECLOUD_NOTIFY_TEST_BOOL", raising=False)

    assert _env_bool("GOREECLOUD_NOTIFY_TEST_BOOL", default=True) is True
    assert _env_bool("GOREECLOUD_NOTIFY_TEST_BOOL", default=False) is False


def test_env_bool_rejects_unrecognized_supplied_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOREECLOUD_NOTIFY_TEST_BOOL", "treu")

    with pytest.raises(ValueError, match="GOREECLOUD_NOTIFY_TEST_BOOL must be one of"):
        _env_bool("GOREECLOUD_NOTIFY_TEST_BOOL")


@pytest.mark.parametrize("touch_minutes", [60, 61])
def test_settings_reject_touch_interval_not_less_than_idle(touch_minutes: int) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "GOREECLOUD_NOTIFY_SESSION_TOUCH_MINUTES must be less than "
            "GOREECLOUD_NOTIFY_SESSION_IDLE_MINUTES"
        ),
    ):
        Settings(session_idle_minutes=60, session_touch_minutes=touch_minutes)


def test_settings_accept_touch_interval_less_than_idle() -> None:
    configured = Settings(session_idle_minutes=60, session_touch_minutes=5)

    assert configured.session_touch_minutes == 5
    assert configured.session_idle_minutes == 60
