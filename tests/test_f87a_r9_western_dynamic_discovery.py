import json

from scripts.f87a_r9_western_dynamic_discovery import run


def test_western_dynamic_discovery_uses_generic_role_swapped_controls(tmp_path):
    result = run(output_dir=tmp_path)
    assert result == json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert result["policy_id"] == "canonical_common_tape_random"
    assert result["seeds"] == [9011, 9012, 9013]
    assert result["game_count"] == 6
    assert result["terminal_discovery_count"] == 1
    assert result["terminal_counts"] == {"CENSORED": 5, "checkmate": 1}
    assert result["dynamic_viability_pass"] is False
    assert result["qualification_effect"] == "DYNAMIC_TERMINAL_DISCOVERY_EVIDENCE_BUT_VIABILITY_STILL_DEFERRED"
    assert all(report["pair_count"] == 1 for report in result["reports"].values())
