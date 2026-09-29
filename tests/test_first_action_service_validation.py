import json

import pytest

from scripts.validate_first_action_service_pilot import FREEZE, OUTPUT, preflight, validate


def test_validation_preflight_reproduces_frozen_vectors_and_rejects_hash_change():
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    reproduced = preflight(frozen)
    assert set(reproduced) == {"western_chess", "standard_shogi"}
    relative = next(iter(frozen["input_sha256"]))
    frozen["input_sha256"][relative] = "0" * 64
    with pytest.raises(RuntimeError, match="hash mismatch"):
        preflight(frozen)


def test_locked_validation_result_reproduces_without_changing_gates():
    frozen_result = json.loads(OUTPUT.read_text(encoding="utf-8"))
    actual = validate()
    assert actual == frozen_result
    assert actual["classification"] == "FIRST_ACTION_SERVICE_VALIDATION_REJECTED"
    assert actual["gate_summary"] == {"western_chess": False, "standard_shogi": True}
    assert actual["xiangqi_human_reference_read"] is False
