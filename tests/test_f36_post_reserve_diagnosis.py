import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "f36_post_reserve_manifest.json"
BASELINE = ROOT / "tests" / "fixtures" / "f36_post_reserve_equal_time_baseline.json"
LADDER = ROOT / "tests" / "fixtures" / "f36_post_reserve_capacity_ladder.json"
CAUSAL = ROOT / "tests" / "fixtures" / "f36_post_reserve_causal_table.json"
SELECTION = ROOT / "tests" / "fixtures" / "f36_post_reserve_selection.json"
STATIC_DIRECT = ROOT / "tests" / "fixtures" / "f36_post_reserve_static_direct_rank.json"
SEARCH = ROOT / "generic_chess" / "ai" / "alphabeta" / "search.py"
CURRENT_SEARCH_SHA = "6b4add054efa0efd6d7def83eda1b5019b4a7d4f3687324a162f286c4adee3ea"


def test_f36_post_reserve_diagnosis_is_frozen_and_selects_one_boundary():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    ladder = json.loads(LADDER.read_text(encoding="utf-8"))
    causal = json.loads(CAUSAL.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    static_direct = json.loads(STATIC_DIRECT.read_text(encoding="utf-8"))

    assert manifest["manifest_sha256"] == "8f7503f9f1d2139bcd92d86270d95fd88b7fd15b8dc9f3e9ea05920b92df5a77"
    assert manifest["current_sandbox_sha"] == "80c1576c4443b4c9311b86fa0d8efbbfa24150ca"
    assert manifest["retained_search_sha256"] == "f9b5faf17b40fcc9f9672875c4d200db7fc5bea314b9da5a20351b95563e3f4e"
    assert hashlib.sha256(SEARCH.read_bytes()).hexdigest() == CURRENT_SEARCH_SHA
    assert manifest["product_authority"] == "a389adc50ed42096874ee38f818584978468c6ac"
    assert manifest["standard_shogi_fingerprint"] == "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
    assert manifest["frozen_inputs"]["f35r1_result"]["sha256"] == "d2d53ab89205feae28a3c1da73b9a9de7650199ab61ce62d40a53c961e19cd30"

    assert static_direct["static_rank_parity"] is True
    assert static_direct["direct_qsearch_rank_parity"] is True
    assert len(static_direct["roots"]) == 10
    assert len(baseline["post_reserve"]["0.5"]) == 10
    assert len(baseline["post_reserve"]["2.0"]) == 10
    assert len(causal) == 10
    assert set(ladder["capacity_aggregates"]["controls"]) == {"0.5", "1.0", "2.0", "4.0", "8.0"}
    assert set(ladder["ladder"]) == set(causal)

    aggregates = selection["aggregate_quantities"]
    assert aggregates == {
        "LONGER_SEARCH_EXTERNAL_RECOVERY_ROOTS": 0,
        "NEXT_ITERATION_NEAR_ROOTS": 0,
        "SHORT_CONTROL_FALLBACK_ROOTS": 8,
        "STABLE_VALUE_MISMATCH_ROOTS": 6,
        "STATIC_TOP3_GAP_ROOTS": 8,
        "TWO_SECOND_DEPTH2_ROOTS": 0,
    }
    assert selection["actionable"] == {
        "classification": "EVALUATOR_VALUE_PRIMARY",
        "evaluator_value": True,
        "search_capacity": False,
    }
    assert selection["selection"]["boundary"] == "F37_RULE_DERIVED_EVALUATOR_REENTRY"
    assert sum(value == "SEARCH_STABLE_VALUE_MISMATCH" for value in (row["causal_classification"] for row in causal.values())) == 6
    assert all(row["causal_classification"] in {"SEARCH_STABLE_VALUE_MISMATCH", "UNRESOLVED"} for row in causal.values())
    assert all(value is True for value in selection["flags"].values())

