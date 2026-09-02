"""H48B: generated benchmark screening is deterministic and pre-learning."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from generic_chess.ai.benchmark.audit_suite import build_compiled, standard_ruleset_specs
from generic_chess.learning.leverage import candidate_specs, select_benchmarks


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "h48b_generated_benchmark_selection.json"
BASELINE_SHA = "d02212e85e9e0b50a946ec74b21e45a315dcb6d8"
SCREEN_REF = "a695fd6e89fb771952e208e562858710ae1e0b3d"


def _data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _direct_eligible(row: dict) -> bool:
    return bool(row["predicate_ledger"]["eligible"])


def test_h48b_ancestry_protocol_and_no_learning_result():
    data = _data()
    assert data["kind"] == "H48B_GENERATED_EVALUATION_SENSITIVE_BENCHMARK_SELECTION"
    assert data["protocol"] == "H48R2A"
    assert data["parent_h48r2a_sha"] == BASELINE_SHA
    assert data["selection_completed_before_learning"] is True
    assert data["learned_checkpoint_input"] is False
    assert subprocess.run(
        ["git", "cat-file", "-e", f"{BASELINE_SHA}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0
    assert not any(key in data for key in ("results", "recovery", "trained_checkpoint"))
    assert all(row["learned_checkpoint_input"] is False for row in data["candidates"])


def test_h48b_has_exact_32_candidate_specs_and_all_rows():
    data = _data()
    rows = sorted(data["candidates"], key=lambda row: row["index"])
    specs = candidate_specs(32)
    assert len(rows) == len(specs) == 32
    assert [(row["index"], row["seed"], row["setup_preset"]) for row in rows] == [
        (spec["index"], spec["seed"], spec["setup_preset"]) for spec in specs
    ]
    assert all(row["board_size"] == 6 for row in rows)
    assert all(row["ruleset_fingerprint"] and row["type_ids"] for row in rows)
    assert all("metrics" in row and "predicate_ledger" in row for row in rows)
    assert all("opening_corpus_id" in row["metrics"] and "corpus_id" in row["metrics"] for row in rows)
    assert all("generation_failed" not in row["violations"] for row in rows)


def test_h48b_dependency_ledgers_match_raw_git_blob_sha256():
    data = _data()
    assert data["screening_implementation_authority"]["ref"] == SCREEN_REF
    assert len(data["screening_implementation_authority"]["paths"]) == 4
    for item in data["execution_dependency_blobs"]:
        raw = subprocess.run(
            ["git", "cat-file", "blob", f"{item['ref']}:{item['path']}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    for item in data["screening_implementation_authority"]["paths"]:
        raw = subprocess.run(
            ["git", "cat-file", "blob", f"{SCREEN_REF}:{item['path']}"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
        assert hashlib.sha256(raw).hexdigest() == item["raw_blob_sha256"]


def test_h48b_predicates_are_explicit_and_recomputed_for_every_row():
    data = _data()
    rows = sorted(data["candidates"], key=lambda row: row["index"])
    assert all(set(row["predicate_ledger"]["predicates"]) == {
        "terminal_rate",
        "average_plies",
        "endless_draw_fraction",
        "owner0_win_rate",
        "owner1_win_rate",
        "tactical_shallow_deep_agreement",
        "evaluation_leverage",
        "forced_move_fraction",
        "mean_legal_actions",
    } for row in rows)
    assert [row["index"] for row in rows if _direct_eligible(row)] == [9, 11, 12, 29]
    assert data["eligible_set"] == [9, 11, 12, 29]
    assert sum(row["predicate_ledger"]["eligible"] for row in rows) == 4


def test_h48b_bound_selector_and_independent_direct_sort_agree():
    data = _data()
    rows = list(data["candidates"])
    specs = {spec["index"]: spec for spec in candidate_specs(32)}
    r2_spec = next(s for s in standard_ruleset_specs() if s.fixture_id == "gen_free_random_4_102")
    r2_fingerprint = build_compiled(r2_spec).ruleset_fingerprint
    reversed_summary = list(reversed(rows))
    bound = select_benchmarks(reversed_summary, r2_fingerprint)["evaluation_sensitive"]
    eligible = [row for row in rows if _direct_eligible(row)]
    direct = sorted(
        eligible,
        key=lambda row: (
            -float(row["metrics"]["eval_leverage"]),
            float(row["metrics"]["owner0_win_rate"]),
            row["ruleset_fingerprint"],
        ),
    )[0]
    expected = {
        "index": direct["index"],
        "seed": direct["seed"],
        "setup_preset": specs[direct["index"]]["setup_preset"],
        "ruleset_fingerprint": direct["ruleset_fingerprint"],
    }
    assert bound == {
        "class": "evaluation_sensitive",
        "index": expected["index"],
        "seed": expected["seed"],
        "ruleset_fingerprint": expected["ruleset_fingerprint"],
    }
    assert data["selection"]["independent_selection_agree"] is True
    assert data["selection"]["bound_selector"] == data["selection"]["direct_sort"]
    assert data["selection"]["selected"] == expected


def test_h48b_selected_ruleset_reconstructs_and_historical_comparison_is_diagnostic():
    data = _data()
    selected = data["selection"]["selected"]
    spec = next(s for s in standard_ruleset_specs() if s.fixture_id == "gen_free_random_4_102")
    generated = None
    from generic_chess.generation.config import GeneratorConfig
    from generic_chess.generation.generator import generate_game

    generated = generate_game(GeneratorConfig(
        seed=selected["seed"],
        board_size=6,
        setup_preset=selected["setup_preset"],
    )).compiled_ruleset
    assert generated.ruleset_fingerprint == selected["ruleset_fingerprint"]
    comparison = data["historical_phase17_comparison"]
    assert comparison["role"] == "diagnostic_only_after_new_selection"
    assert comparison["selected_index_matches"] is True
    assert comparison["selected_fingerprint_matches_prefix"] is True
    assert len(data["selection"]["selected"]) == 4
