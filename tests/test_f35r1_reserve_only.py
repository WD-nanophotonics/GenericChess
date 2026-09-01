import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f35r1_reserve_only_manifest.json"
RESULT = ROOT / "tests" / "fixtures" / "f35r1_reserve_only_results.json"
ACCESSIBILITY = ROOT / "tests" / "fixtures" / "f35r1_reserve_only_accessibility.json"
BASELINE = ROOT / "tests" / "fixtures" / "f35r1_reserve_only_baseline.json"
SEARCH = ROOT / "generic_chess" / "ai" / "alphabeta" / "search.py"


def test_f35r1_is_reserve_only_and_retained():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    accessibility = json.loads(ACCESSIBILITY.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert manifest["manifest_sha256"] == "e6446cb1d436e6bcabf71dfc188bb4a3fbd4933fabf7b702981feb86f67a4fdb"
    assert manifest["pre_run_sandbox_sha"] == "b02d92e0aabaf41b547cd8fa8fdb550e7dc756cb"
    assert manifest["f34_baseline_sha"] == "4fa6b5d45ed1600645d2b3b0cb39fcfb8837cc81"
    assert manifest["f34_search_sha"] == "657cbd8d3bc623b3aa20dc88674f3f43edb0c9af"
    assert manifest["provisional_commit"] == "b02d92e0aabaf41b547cd8fa8fdb550e7dc756cb"
    assert manifest["corrective_search_sha"] == hashlib.sha256(SEARCH.read_bytes()).hexdigest()

    assert result["status"] == "PASS"
    assert result["retained"] is True
    assert result["next_boundary"] == "F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE"
    assert result["production_search_post_change_sha"] == hashlib.sha256(SEARCH.read_bytes()).hexdigest()
    assert result["fixed_node_gate"] is True
    assert all(result["gates"].values())
    assert result["source_scope"]["FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE"] is True
    assert result["source_scope"]["LAZY_NONCHECK_LEGAL_GENERATION_RETAINED"] is False
    assert result["direct_and_zero_qdepth_witness"] == {
        "direct_internal_configured_qdepth_four": True,
        "explicit_qdepth_zero_static_eval": True,
    }
    assert result["safety"]["status"] == "PASS"
    assert result["first_iteration_in_check_evasion"]["passed"] is True
    assert all(result["reserve_state_witness"].values())
    assert result["cancellation_witness"]["fresh_context_after_cancel"] is True
    assert result["external_descriptive_comparison"]["alphasho_rerun"] is False
    assert result["external_descriptive_comparison"]["used_for_selection"] is False

    for variant, controls in result["fixed_node"].items():
        assert set(controls) == {"512", "2048"}
        assert all(len(rows) == 10 for rows in controls.values())
    for rows in result["fixed_node"]["production_candidate"].values():
        assert all(all(row["parity"].values()) for row in rows.values())

    assert accessibility["controls"]["0.5"]["fallback_events"] == {
        "production_candidate": 24,
        "shadow_baseline": 30,
    }
    assert accessibility["controls"]["0.5"]["fallback_roots_improved"] == 3
    assert accessibility["controls"]["2.0"]["retention_statistic"] >= 0.20
    assert accessibility["controls"]["2.0"]["fallback_events"] == {
        "production_candidate": 0,
        "shadow_baseline": 0,
    }
    assert result["accessibility"]["gate"] is True
    assert set(baseline["shadow_baseline"]) == {"512", "2048"}
    for variant in ("shadow_baseline", "production_candidate"):
        for control in ("0.5", "2.0"):
            assert all(len(rows) == 3 for rows in result["wall_time"][variant][control].values())

