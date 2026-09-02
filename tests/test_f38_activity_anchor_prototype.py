import json
import subprocess
from pathlib import Path

from scripts.historical_validation import historical_scope_unchanged_worktree

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_f38_prototype_identity_and_scope():
    report = load("f38_activity_anchor_prototype_identity.json")
    assert report["status"] == "PASS"
    assert report["candidate"] == "R37C"
    assert report["score_identity"] is True
    assert report["mismatches"] == []
    assert report["generic_transfer_contract"]["passed"] is True
    assert report["no_candidate_evaluator_implementation_call"] is True
    assert report["production_diff_zero"] is True


def test_f38_holdout_and_selection_are_recorded():
    ranks = load("f38_activity_anchor_holdout_ranks.json")
    search = load("f38_activity_anchor_holdout_search.json")
    cost = load("f38_activity_anchor_micro_cost.json")
    selection = load("f38_activity_anchor_selection.json")
    assert ranks["summary"]["holdout_size"] == 20
    assert len(ranks["rows"]) == 20
    assert search["candidate"] == "R37C"
    assert search["original_ten_root_identity"]["512"]["complete"] is True
    assert search["original_ten_root_identity"]["2048"]["complete"] is True
    assert search["original_ten_root_identity"]["512"]["exact_identity_count"] == 0
    assert search["original_ten_root_identity"]["2048"]["exact_identity_count"] == 0
    assert cost["gate"] is True
    assert ranks["status"] == "FAIL"
    assert selection["selected_boundary"] == "F38A_R37C_PROTOTYPE_PARITY_DIAGNOSIS"
    assert selection["candidate"] == "R37C"
    assert selection["gates"]["exact_identity"] is True
    assert selection["gates"]["generic_transfer"] is True
    assert selection["gates"]["original_ten_root_search_identity"] is False
    assert selection["F39_IMPLEMENTATION_ELIGIBLE"] is False


def test_f38_production_scope():
    assert historical_scope_unchanged_worktree()
