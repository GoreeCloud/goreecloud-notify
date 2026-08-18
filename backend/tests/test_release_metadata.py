from app.main import (
    ACCEPTANCE_GATES,
    ACCEPTANCE_STATUS,
    PRODUCTION_ACCEPTED,
    RELEASE_STAGE,
    api_meta,
)


def test_release_metadata_distinguishes_runtime_mode_from_acceptance() -> None:
    meta = api_meta()

    assert meta["runtime_environment"] in {"development", "test", "production"}
    assert meta["production"] is (meta["runtime_environment"] == "production")
    assert meta["production_configuration"] is meta["production"]

    assert RELEASE_STAGE == "release_candidate"
    assert PRODUCTION_ACCEPTED is False
    assert ACCEPTANCE_STATUS == "pending"
    assert meta["release_stage"] == RELEASE_STAGE
    assert meta["production_accepted"] is False
    assert meta["acceptance_status"] == ACCEPTANCE_STATUS
    assert meta["acceptance_gates"] == ACCEPTANCE_GATES


def test_current_acceptance_gates_remain_explicitly_pending() -> None:
    assert ACCEPTANCE_GATES == {
        "backup_restore": "pending",
        "independent_monitoring": "pending",
        "target_runtime_publication": "pending",
        "manual_browser_os": "pending",
    }
