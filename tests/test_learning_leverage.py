"""Learning Phase 1.7: evaluation leverage / benchmark identification tests."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.diagnostics import generate_diagnostic_corpus
from generic_chess.learning.leverage import (
    EVAL_LEVERAGE_BUDGET,
    SINGLE_PIECE_FACTORS,
    PerturbationSpec,
    apply_perturbation,
    budget_sweep,
    candidate_specs,
    eval_leverage,
    merge_performance,
    perturbation_specs,
    product_budget_analysis,
    pre_registered_config,
    screen_candidates,
    select_benchmarks,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, requires_native


def _setup(size=4, seed=7):
    compiled = generated_compiled(size=size, seed=seed)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    gen0 = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=seed
    )
    rules = compile_native_rules(compiled)
    return compiled, rules, gen0


def _corpus(compiled, count=8, seed=42):
    openings = generate_arena_openings(compiled, count=2, seed=314159)
    return generate_diagnostic_corpus(
        compiled, openings, count=count, seed=seed, max_plies=20
    )


def _single_spec(compiled, factor=1.25):
    return next(
        s
        for s in perturbation_specs(compiled)
        if s.kind == "single_piece"
        and float(s.params["factor"]) == factor
    )


def test_pre_registered_config_stable():
    cfg = pre_registered_config()
    assert cfg["eval_leverage_budget"] == EVAL_LEVERAGE_BUDGET == 2000
    assert cfg["sweep_budgets"] == [250, 500, 1000, 2000, 4000, 8000]
    assert cfg["eligibility"]["leverage_min"] == 0.10
    assert cfg["candidate_count"] == 32
    # The protocol itself never changes when a smoke run happens; smoke only
    # adds an "effective" override map (mode is injected by the CLI, not the
    # protocol).
    assert "mode" not in cfg


def test_merge_performance_accumulates_and_overwrites():
    base = merge_performance(
        None, [{"phase": "perturbation_sweep", "elapsed_seconds": 10.0}]
    )
    merged = merge_performance(
        base,
        [
            {"phase": "budget_sweep", "elapsed_seconds": 20.0},
            {"phase": "perturbation_sweep", "elapsed_seconds": 12.0},
        ],
    )
    by_name = {e["phase"]: e["elapsed_seconds"] for e in merged["phases"]}
    assert by_name["perturbation_sweep"] == 12.0
    assert by_name["budget_sweep"] == 20.0
    assert merged["total_elapsed_seconds"] == pytest.approx(32.0)


def test_perturbation_deterministic_and_gen0_not_mutated():
    compiled, _rules, gen0 = _setup()
    before_id = gen0.checkpoint_id
    before_weights = dict(gen0.board_weights)
    spec = _single_spec(compiled, 1.25)
    tid = spec.params["type_id"]
    perturbed, info = apply_perturbation(gen0, spec)
    assert perturbed is not None
    assert not info["skipped"]
    assert perturbed.checkpoint_id != gen0.checkpoint_id
    assert perturbed.board_weights[tid] == pytest.approx(
        gen0.board_weights[tid] * 1.25
    )
    # Only the perturbed type changes; base stays byte-identical.
    for t, w in gen0.board_weights.items():
        if t != tid:
            assert perturbed.board_weights[t] == pytest.approx(w)
    assert gen0.checkpoint_id == before_id
    assert gen0.board_weights == before_weights
    assert info["delta_weight_l2"] > 0.0
    # Deterministic: same spec -> same perturbed checkpoint.
    again, _info2 = apply_perturbation(gen0, spec)
    assert again.checkpoint_id == perturbed.checkpoint_id


def test_zero_weight_type_skipped_explicitly():
    compiled, _rules, gen0 = _setup()
    tid = next(iter(gen0.board_weights))
    zero = gen0.child_checkpoint(
        board_weights={t: 0.0 for t in gen0.board_weights},
        hand_weights=dict(gen0.hand_weights),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=0,
        training_config_hash="zero",
        training_seed=7,
    )
    spec = PerturbationSpec(
        name="zero_probe",
        kind="single_piece",
        params={"type_id": tid, "factor": 1.25},
    )
    perturbed, info = apply_perturbation(zero, spec)
    assert perturbed is None
    assert info["skipped"] is True
    assert info["reason"] == "zero_weight_type"


def test_directional_perturbation_l2_and_determinism():
    compiled, _rules, gen0 = _setup()
    base_l2 = sum(
        v * v
        for v in list(gen0.board_weights.values())
        + list(gen0.hand_weights.values())
    ) ** 0.5
    seen: set[str] = set()
    for spec in perturbation_specs(compiled):
        if spec.kind != "directional":
            continue
        perturbed, info = apply_perturbation(gen0, spec)
        assert perturbed is not None
        assert info["delta_weight_l2"] == pytest.approx(
            0.25 * base_l2, rel=1e-6
        )
        assert perturbed.checkpoint_id not in seen
        seen.add(perturbed.checkpoint_id)
    assert len(seen) == 4


@requires_native
def test_eval_leverage_deterministic_and_bounded():
    compiled, rules, gen0 = _setup()
    corpus = _corpus(compiled)
    a = eval_leverage(compiled, rules, gen0, corpus)
    b = eval_leverage(compiled, rules, gen0, corpus)
    assert a == b
    assert 0.0 <= a["flip_rate"] <= 1.0
    assert a["positions"] == len(corpus.positions)


@requires_native
def test_budget_sweep_rerun_identical():
    compiled, rules, gen0 = _setup()
    child = gen0.child_checkpoint(
        board_weights={t: v * 1.1 for t, v in gen0.board_weights.items()},
        hand_weights={t: v * 0.9 for t, v in gen0.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="test",
        training_seed=7,
    )
    corpus = _corpus(compiled, count=4)
    a = budget_sweep(
        compiled, rules, [gen0, child], corpus, budgets=(250, 500)
    )
    b = budget_sweep(
        compiled, rules, [gen0, child], corpus, budgets=(250, 500)
    )
    assert a == b
    assert set(a["per_budget"]) == {"250", "500"}
    assert a["per_budget"]["250"]["learned"]["1"]["positions"] == 4


def test_candidate_specs_deterministic():
    a = candidate_specs(4)
    b = candidate_specs(4)
    assert a == b
    assert len({s["seed"] for s in a}) == 4
    assert a[0]["index"] == 0
    assert a[0]["board_size"] == 6


@requires_native
def test_screen_candidates_records_all(tmp_path):
    summaries = screen_candidates(tmp_path, count=2)
    assert len(summaries) == 2
    for s in summaries:
        assert "eligible" in s
        assert s["eligible"] is False or s["ruleset_fingerprint"]
        if s["eligible"]:
            assert "metrics" in s


def test_select_benchmarks_no_checkpoint_access_and_deterministic():
    sig = inspect.signature(select_benchmarks)
    assert list(sig.parameters) == ["candidate_summaries", "r2_fingerprint"]

    def summary(index, leverage, agreement, owner0=0.5, owner1=0.3):
        return {
            "index": index,
            "seed": 1,
            "ruleset_fingerprint": f"fp{index}",
            "eligible": True,
            "metrics": {
                "eval_leverage": leverage,
                "owner0_win_rate": owner0,
                "owner1_win_rate": owner1,
                "tactical_shallow_deep_agreement": agreement,
                "average_plies": 30,
                "forced_move_fraction": 0.1,
                "mean_legal_actions": 6,
                "endless_draw_fraction": 0.0,
                "terminal_rate": 1.0,
            },
        }

    pool = [
        summary(0, 0.30, 0.80),  # high leverage -> evaluation-sensitive
        summary(1, 0.15, 0.70),  # mid leverage+agreement -> mixed
        summary(2, 0.03, 0.95),  # low leverage -> neither
    ]
    selection = select_benchmarks(pool, "r2fp")
    assert selection["evaluation_sensitive"]["index"] == 0
    assert selection["mixed"]["index"] == 1
    assert selection["tactical"]["ruleset_fingerprint"] == "r2fp"
    # Deterministic rerun.
    assert select_benchmarks(pool, "r2fp") == selection
    # Low-leverage candidate can never be selected as evaluation-sensitive.
    low_only = [summary(2, 0.03, 0.95)]
    sel2 = select_benchmarks(low_only, "r2fp")
    assert sel2["evaluation_sensitive"] is None
    assert sel2["mixed"] is None


def test_frozen_checkpoint_unchanged_after_perturbations():
    compiled, _rules, gen0 = _setup()
    before = gen0.checkpoint_id
    for spec in perturbation_specs(compiled):
        apply_perturbation(gen0, spec)
    assert gen0.checkpoint_id == before


def test_product_budget_analysis_uses_evaluation_sensitive_retest():
    def retest(flip_at_250, teacher=0.6):
        return {
            "teacher": {"best_move_agreement": {"0": teacher}},
            "search_sensitivity": {
                "250": {
                    "1": {"move_flip_rate": flip_at_250},
                    "2": {"move_flip_rate": flip_at_250},
                    "3": {"move_flip_rate": flip_at_250},
                },
                "500": {
                    "1": {"move_flip_rate": 0.0},
                    "2": {"move_flip_rate": 0.0},
                    "3": {"move_flip_rate": 0.0},
                },
            },
            "raw_search_sensitivity": {
                "250": {
                    "1": [{"best_action": "A"}],
                    "2": [{"best_action": "A"}],
                    "3": [{"best_action": "A"}],
                },
                "500": {
                    "1": [{"best_action": "A"}],
                    "2": [{"best_action": "A"}],
                    "3": [{"best_action": "A"}],
                },
            },
        }

    out = product_budget_analysis(retest(0.05))
    assert out["product_budget"] == 250
    assert out["per_budget"][0]["learned_mean_flip_rate"] == pytest.approx(0.05)
    # No learned flip anywhere -> no product budget.
    none_out = product_budget_analysis(retest(0.0))
    assert none_out["product_budget"] == "NO_PRODUCT_BUDGET_IDENTIFIED"
    # Failed searches block the budget even when flips are visible.
    bad = retest(0.05)
    bad["raw_search_sensitivity"]["250"]["1"] = [{"best_action": "None"}]
    bad_out = product_budget_analysis(bad)
    assert bad_out["product_budget"] == "NO_PRODUCT_BUDGET_IDENTIFIED"


def test_single_piece_factor_definition_matches_protocol():
    compiled, _rules, _gen0 = _setup()
    factors = sorted(
        {
            float(s.params["factor"])
            for s in perturbation_specs(compiled)
            if s.kind == "single_piece"
        }
    )
    assert factors == sorted(SINGLE_PIECE_FACTORS)
