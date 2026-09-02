import hashlib
import json
import subprocess
from pathlib import Path

from scripts.historical_validation import historical_scope_unchanged_worktree

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "f38r1_frozen_r37c_search_parity.json"


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_f38r1_binds_and_replays_frozen_r37c_search_exactly():
    report = load()
    assert report["status"] == "PASS"
    assert report["production_diff_zero"] is True
    assert report["parity"]["protocol"] == {
        "roots": 10,
        "budgets": [512, 2048],
        "max_depth": 8,
        "qsearch": "4/8",
        "fresh_tt_per_run": True,
        "native_requested": True,
        "timing_fields_excluded": True,
        "deterministic_fields": [
            "selected_move",
            "score",
            "pv_head",
            "completed_depth",
            "nodes",
            "qnodes",
            "termination_reason",
        ],
    }
    for budget in ("512", "2048"):
        for name in (
            "F37_ORACLE_REPLAY_PARITY",
            "PROTOTYPE_VS_F37_FROZEN_PARITY",
            "PROTOTYPE_VS_F37_ORACLE_REPLAY_PARITY",
        ):
            summary = report["parity"]["by_budget"][budget][name]
            assert summary["run_count"] == 10
            assert summary["exact_identity_count"] == 10
            assert summary["passed"] is True
            assert summary["first_divergent_row"] is None
    for summary in report["parity"]["all_runs"].values():
        assert summary == {
            "run_count": 20,
            "exact_identity_count": 20,
            "passed": True,
            "first_divergent_row": None,
        }


def test_f38r1_preserves_first_pass_evidence_and_reclassifies_boundary():
    report = load()
    expected_bound = {
        "f37_search_shadow",
        "f37_representation_ranks",
        "f37_selection",
        "f37_r1_recertification",
        "h38a_manifest",
        "h38a_descriptor",
        "f38_prototype_script",
        "f38_prototype_identity",
        "f38_holdout_ranks",
        "f38_holdout_search",
        "f38_micro_cost",
        "f38_first_pass_selection",
    }
    assert set(report["evidence_bindings"]) == expected_bound
    assert report["evidence_bindings"]["f38_prototype_script"]["sha256"] == "d45bef8c62611ecbeb5501bc3d1bcd13b24f450d5b34680706123537fda0457b"
    corrected = {
        "scripts/audit_f38_activity_anchor_prototype.py": "28df6bc78b40e4a3c7323a9d160b7fc4493c6351a375b79b66e10e4fbfdb483b",
    }
    for binding in report["evidence_bindings"].values():
        path = ROOT / binding["path"]
        expected = corrected.get(binding["path"], binding["sha256"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    outcome = report["reclassification"]
    assert outcome["first_pass_defect"] == "WRONG_ORIGINAL_SEARCH_PARITY_ORACLE"
    assert outcome["first_pass_mechanically_compared"] == "ProductionShapedR37CPrototype == V1 production evaluator"
    assert outcome["required_comparison"] == "ProductionShapedR37CPrototype == frozen F37 R37C"
    assert outcome["gates"] == {
        "exact_static_identity": True,
        "original_ten_root_r37c_search_identity": True,
        "generic_transfer": True,
        "holdout_corpus": True,
        "holdout_static_signal": False,
        "micro_cost": True,
        "independent_search_cost": True,
        "independent_search_signal": False,
        "runtime_2s_safety": True,
    }
    assert outcome["F39_IMPLEMENTATION_ELIGIBLE"] is False
    assert outcome["selected_boundary"] == "F39_EVALUATOR_REENTRY_GENERALIZATION_CORRECTIVE"
    assert all(outcome["flags"].values())
    assert report["no_rerun"] == {
        "alphasho": True,
        "paired_benchmark": True,
        "holdout_reselection": True,
        "candidate_formula_change": True,
        "production_change": True,
    }


def test_f38r1_production_scope():
    assert historical_scope_unchanged_worktree()
