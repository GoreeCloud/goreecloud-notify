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


def test_settings_accepts_development_build_revision_outside_production() -> None:
    configured = Settings(build_revision="development")

    assert configured.build_revision == "development"


def test_settings_rejects_malformed_build_revision() -> None:
    with pytest.raises(ValueError, match="build_revision must be 'development'"):
        Settings(build_revision="main")


def test_settings_reject_invalid_trusted_proxy_network() -> None:
    with pytest.raises(
        ValueError,
        match="GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS contains invalid network",
    ):
        Settings(trusted_proxy_cidrs=("not-a-network",))


def test_settings_accept_valid_trusted_proxy_networks() -> None:
    configured = Settings(
        trusted_proxy_cidrs=("10.0.0.0/8", "fd00::/8"),
    )

    assert configured.trusted_proxy_cidrs == ("10.0.0.0/8", "fd00::/8")


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValueError, match="GOREECLOUD_NOTIFY_ENVIRONMENT must be one of"):
        Settings(environment="prod")


def test_production_requires_secure_cookie() -> None:
    with pytest.raises(
        ValueError,
        match="GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE must be true in production",
    ):
        Settings(
            environment="production",
            session_cookie_secure=False,
            cors_origins=("https://notify.goreecloud.com",),
            trusted_proxy_cidrs=("172.30.0.0/24",),
        )


@pytest.mark.parametrize(
    "origin",
    [
        "http://notify.goreecloud.com",
        "http://localhost:5173",
        "https://127.0.0.1",
        "https://notify.goreecloud.com/path",
        "https://notify.goreecloud.com?debug=1",
    ],
)
def test_production_rejects_non_https_local_or_non_origin_cors_values(origin: str) -> None:
    with pytest.raises(ValueError, match="GOREECLOUD_NOTIFY_CORS_ORIGINS"):
        Settings(
            environment="production",
            session_cookie_secure=True,
            cors_origins=(origin,),
            trusted_proxy_cidrs=("172.30.0.0/24",),
        )


def test_production_requires_explicit_trusted_proxy_network() -> None:
    with pytest.raises(
        ValueError,
        match="GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS must identify",
    ):
        Settings(
            environment="production",
            session_cookie_secure=True,
            cors_origins=("https://notify.goreecloud.com",),
            trusted_proxy_cidrs=(),
        )


def test_production_rejects_trusting_entire_address_family() -> None:
    with pytest.raises(
        ValueError,
        match="GOREECLOUD_NOTIFY_TRUSTED_PROXY_CIDRS cannot trust an entire address family",
    ):
        Settings(
            environment="production",
            session_cookie_secure=True,
            cors_origins=("https://notify.goreecloud.com",),
            trusted_proxy_cidrs=("0.0.0.0/0",),
        )


def test_production_requires_immutable_build_revision() -> None:
    with pytest.raises(
        ValueError,
        match="production requires an immutable Git build revision",
    ):
        Settings(
            environment="production",
            build_revision="development",
            session_cookie_secure=True,
            cors_origins=("https://notify.goreecloud.com",),
            trusted_proxy_cidrs=("172.30.5.0/24",),
        )


def test_production_accepts_private_https_origin_narrow_proxy_and_build_revision() -> None:
    configured = Settings(
        environment="production",
        build_revision="a" * 40,
        session_cookie_secure=True,
        cors_origins=("https://notify.goreecloud.com",),
        trusted_proxy_cidrs=("172.30.5.0/24",),
    )

    assert configured.environment == "production"
    assert configured.build_revision == "a" * 40
    assert configured.session_cookie_secure is True
