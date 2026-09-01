import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_f37_manifest_and_production_scope():
    manifest = load("f37_evaluator_reentry_manifest.json")
    assert manifest["manifest_sha256"] == "f9c973859bd816f66cf733699c5b5940c356d0599f360b898a8bbe58ee0c9956"
    assert manifest["current_sandbox_sha"] == "91e586fe45baed0b055892d980ada21ec3d57a35"
    assert manifest["product_authority"] == "a389adc50ed42096874ee38f818584978468c6ac"
    assert manifest["standard_shogi_fingerprint"] == "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
    assert manifest["candidate_definitions"] == {
        "R37A": "PIECE_LOCAL_REALIZED_ACTIVITY_REPLACEMENT",
        "R37B": "ANCHOR_RING_CONTROL_REPLACEMENT",
        "R37C": "ACTIVITY_PLUS_ANCHOR_RING_REPLACEMENT",
    }
    assert subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0


def test_f37_decomposition_and_static_gates():
    decomposition = load("f37_evaluator_v1_decomposition.json")
    assert decomposition["full_v1"]["parity"] is True
    assert decomposition["stable_mismatch_summary"]["stable_root_count"] == 6
    ranks = load("f37_evaluator_representation_ranks.json")
    assert ranks["baselines"] == {"AS050_TOP3_GAP_ROOTS": 8, "AS200_TOP3_GAP_ROOTS": 6}
    assert ranks["summary"]["R37A"]["static_signal_gate"] is False
    assert ranks["summary"]["R37B"]["static_signal_gate"] is True
    assert ranks["summary"]["R37C"]["static_signal_gate"] is True
    assert ranks["summary"]["R37B"]["stable_best_rank_strict_improvements"] == 5
    assert ranks["summary"]["R37C"]["stable_best_rank_strict_improvements"] == 6
    assert ranks["summary"]["R37C"]["stable_best_rank_worsened"] == 0


def test_f37_search_gates_and_selection():
    shadow = load("f37_evaluator_search_shadow.json")
    assert set(shadow["candidate_gates"]) == {"R37B", "R37C"}
    assert all(row["search_cost_gate"] and row["search_signal_gate"] for row in shadow["candidate_gates"].values())
    assert shadow["runtime_2s"]["R37B"]["depth_regressions"] == 1
    assert shadow["runtime_2s"]["R37C"]["depth_regressions"] == 0
    assert shadow["runtime_2s"]["R37B"]["new_fallback_roots"] == 0
    assert shadow["runtime_2s"]["R37C"]["new_fallback_roots"] == 0
    selection = load("f37_evaluator_selection.json")
    assert selection["eligible_candidates"] == ["R37B", "R37C"]
    assert selection["selected_candidate"] == "R37C"
    assert selection["selected_boundary"] == "F38_ACTIVITY_AND_ANCHOR_CONTROL_EVALUATOR_PROTOTYPE"
    assert all(selection["flags"].values())

