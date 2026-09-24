from pathlib import Path

from scripts.static_material_v2g_validator_provenance import (
    FROZEN_VALIDATOR_SHA256,
    VALIDATOR_RELATIVE_PATH,
    check_validator_version,
)

ROOT = Path(__file__).resolve().parents[1]


def _freeze(recorded_validator_sha: str = FROZEN_VALIDATOR_SHA256) -> dict:
    return {"sha256": {VALIDATOR_RELATIVE_PATH: recorded_validator_sha}}


def test_accepts_only_the_recorded_frozen_and_reviewed_current_pair() -> None:
    result = check_validator_version(
        _freeze(), ROOT / VALIDATOR_RELATIVE_PATH
    )
    assert result["approved"] is True
    assert result["current_sha256"] == result["expected_reviewed_current_sha256"]


def test_rejects_an_unreviewed_current_validator_file() -> None:
    result = check_validator_version(_freeze(), Path(__file__).resolve())
    assert result["approved"] is False


def test_rejects_a_changed_frozen_validator_record() -> None:
    result = check_validator_version(_freeze("0" * 64), ROOT / VALIDATOR_RELATIVE_PATH)
    assert result["approved"] is False
