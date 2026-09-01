import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f35_first_iteration_reserve_manifest.json"
RESULT = ROOT / "tests" / "fixtures" / "f35_q34c_fixed_node_parity.json"
ACCESSIBILITY = ROOT / "tests" / "fixtures" / "f35_first_iteration_reserve_accessibility.json"
BASELINE = ROOT / "tests" / "fixtures" / "f35_first_iteration_reserve_baseline.json"
SEARCH = ROOT / "generic_chess" / "ai" / "alphabeta" / "search.py"


def test_f35_first_iteration_reserve_is_retained_with_frozen_gates():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    accessibility = json.loads(ACCESSIBILITY.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert manifest["manifest_sha256"] == "cb2afd22c4235cbafb7804dc80a6ba44cf5c2a38a2ed21d36ca5f0dd94b35787"
    assert manifest["pre_run_sandbox_sha"] == "4fa6b5d45ed1600645d2b3b0cb39fcfb8837cc81"
    assert manifest["production_search_pre_change_sha"] == "657cbd8d3bc623b3aa20dc88674f3f43edb0c9af"
    assert result["status"] == "PASS"
    assert result["retained"] is True
    assert result["next_boundary"] == "F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE"
    assert result["production_changed"] is True
    assert result["production_search_post_change_sha"] == hashlib.sha256(SEARCH.read_bytes()).hexdigest()
    assert result["f34_manifest_sha256"] == "6a5600c4fc1fb82582b42d47235fd72b4e02d60322749e1b97ebbae98500b75d"
    assert result["fixed_node_gate"] is True
    assert all(result["gates"].values())
    assert result["safety"]["status"] == "PASS"
    assert result["safety"]["push_pop_balance"] is True
    assert result["evaluator_context"]["modified"] is False
    assert result["external_descriptive_comparison"]["alphasho_rerun"] is False
    assert result["external_descriptive_comparison"]["used_for_selection"] is False

    witness = result["reserve_state_witness"]
    assert all(witness.values())
    assert result["first_iteration_in_check_evasion"]["passed"] is True
    assert result["cancellation_witness"]["fresh_context_after_cancel"] is True
    assert result["cancellation_witness"]["termination_reason"] == "cancelled"

    assert accessibility["gate"] is True
    assert set(accessibility) >= {"0.5", "2.0", "depth_regression_gate", "gate"}
    assert set(baseline["shadow_baseline"]) == {"512", "2048"}
    assert set(result["fixed_search_regression"]) == {"128", "256", "512", "1024", "2048"}
    for variant in ("shadow_baseline", "production_candidate"):
        for control in ("0.5", "2.0"):
            assert all(len(repetitions) == 3 for repetitions in result["wall_time"][variant][control].values())

    for variant, controls in result["fixed_node"].items():
        assert set(controls) == {"512", "2048"}
        assert all(len(rows) == 10 for rows in controls.values())
    for rows in result["fixed_node"]["production_candidate"].values():
        for row in rows.values():
            assert all(row["parity"].values())
