"""Learning Phase 1.6: signal diagnostics tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.learning.diagnostics import (
    LearningDiagnosticCorpus,
    arena_sensitivity,
    evaluator_change_diagnostics,
    feature_bottleneck_diagnostics,
    generate_diagnostic_corpus,
    search_sensitivity_diagnostics,
    td_signal_diagnostics,
    teacher_benchmark,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, requires_native


def _setup(size=4, seed=7):
    compiled = generated_compiled(size=size, seed=seed)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    checkpoint = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=seed
    )
    rules = compile_native_rules(compiled)
    return compiled, rules, checkpoint


def _corpus(compiled):
    openings = generate_arena_openings(compiled, count=4, seed=314159)
    return generate_diagnostic_corpus(
        compiled, openings, count=24, seed=42, max_plies=20
    )


def test_corpus_deterministic_and_replayable():
    compiled, _rules, _cp = _setup()
    openings = generate_arena_openings(compiled, count=4, seed=314159)
    a = generate_diagnostic_corpus(compiled, openings, count=24, seed=42)
    b = generate_diagnostic_corpus(compiled, openings, count=24, seed=42)
    c = generate_diagnostic_corpus(compiled, openings, count=24, seed=43)
    assert a.corpus_id == b.corpus_id
    assert a.corpus_id != c.corpus_id
    restored = LearningDiagnosticCorpus.from_dict(a.to_dict())
    assert restored.corpus_id == a.corpus_id
    restored.validate(compiled)
    other = generated_compiled(size=6, seed=11)
    with pytest.raises(ValueError):
        restored.validate(other)


def test_corpus_checkpoint_independent():
    compiled, _rules, cp = _setup()
    openings = generate_arena_openings(compiled, count=4, seed=314159)
    corpus = generate_diagnostic_corpus(compiled, openings, count=12, seed=1)
    modified = cp.child_checkpoint(
        board_weights={k: v + 7 for k, v in cp.board_weights.items()},
        hand_weights={k: v + 7 for k, v in cp.hand_weights.items()},
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash="x",
        training_seed=7,
    )
    assert modified.checkpoint_id != cp.checkpoint_id
    corpus2 = generate_diagnostic_corpus(compiled, openings, count=12, seed=1)
    assert corpus.corpus_id == corpus2.corpus_id


@requires_native
def test_td_instrumentation_does_not_change_learner():
    compiled, rules, checkpoint = _setup()
    config = SelfPlayConfig(games=2, nodes_per_move=200, max_depth=4, seed=5)
    trajectories = collect_self_play(compiled, rules, checkpoint, config)
    td_cfg = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=0.1)
    result = tdleaf_update(trajectories, checkpoint, td_cfg)
    records, _summary, board_delta, hand_delta = td_signal_diagnostics(
        trajectories, checkpoint, td_cfg
    )
    assert records
    # Applying the diagnostic's deltas must reproduce tdleaf_update's child.
    board = {
        t: checkpoint.board_weights[t] + board_delta.get(t, 0.0)
        for t in checkpoint.board_weights
    }
    hand = {
        t: checkpoint.hand_weights[t] + hand_delta.get(t, 0.0)
        for t in checkpoint.hand_weights
    }
    candidate = LearnableMaterialCheckpoint(
        ruleset_fingerprint=checkpoint.ruleset_fingerprint,
        evaluation_profile_version=checkpoint.evaluation_profile_version,
        generation=1,
        parent_checkpoint_id=None,
        created_at=checkpoint.created_at,
        board_weights=board,
        hand_weights=hand,
        material_scale=checkpoint.material_scale,
        value_scale=checkpoint.value_scale,
        reference_median=checkpoint.reference_median,
        w_max=checkpoint.w_max,
    )
    candidate.normalize_and_clip()
    for t in checkpoint.board_weights:
        assert candidate.board_weights[t] == pytest.approx(
            result.board_weights[t], abs=1e-8
        )
        assert candidate.hand_weights[t] == pytest.approx(
            result.hand_weights[t], abs=1e-8
        )


def test_feature_bottleneck_counts():
    compiled, _rules, _cp = _setup()
    corpus = _corpus(compiled)
    stats = feature_bottleneck_diagnostics(compiled, corpus)
    assert stats["total_positions"] == len(corpus.positions)
    assert 0.0 <= stats["unique_ratio"] <= 1.0
    assert stats["collision_group_count"] >= 0
    assert stats["zero_vector_fraction"] >= 0.0


def test_evaluator_change_identical_is_zero():
    compiled, _rules, checkpoint = _setup()
    corpus = _corpus(compiled)
    out = evaluator_change_diagnostics(
        compiled, [checkpoint, checkpoint], corpus
    )
    assert out["1"]["mean_abs_delta"] == 0.0
    assert out["1"]["exactly_unchanged_fraction"] == 1.0


@requires_native
def test_search_sensitivity_identical_evaluator_zero_flip():
    compiled, rules, checkpoint = _setup()
    corpus = _corpus(compiled)
    out, results = search_sensitivity_diagnostics(
        compiled, rules, [checkpoint, checkpoint], corpus, nodes=300
    )
    assert out["1"]["move_flip_rate"] == 0.0
    assert out["1"]["pv_first_disagreement_rate"] == 0.0
    # Deterministic rerun.
    out2, results2 = search_sensitivity_diagnostics(
        compiled, rules, [checkpoint, checkpoint], corpus, nodes=300
    )
    assert results == results2


@requires_native
def test_teacher_benchmark_deterministic():
    compiled, rules, checkpoint = _setup()
    corpus = _corpus(compiled)
    out = teacher_benchmark(
        compiled, rules, [checkpoint, checkpoint], corpus,
        student_nodes=200, teacher_nodes=400,
    )
    assert out["positions"] > 0
    assert 0.0 <= out["best_move_agreement"]["0"] <= 1.0
    assert out["student_nodes"] == 200
    out2 = teacher_benchmark(
        compiled, rules, [checkpoint, checkpoint], corpus,
        student_nodes=200, teacher_nodes=400,
    )
    assert out == out2


@requires_native
def test_arena_sensitivity_runs():
    compiled, rules, checkpoint = _setup()
    openings = generate_arena_openings(compiled, count=4, seed=314159)
    out = arena_sensitivity(
        compiled, rules, checkpoint, openings,
        budget_pairs=(("400", "100"),), pairs=4,
    )
    entry = out["400_vs_100"]
    assert entry["pairs"] == 4
    assert 0.0 <= entry["weak_side_mean_pair_score"] <= 1.0


@requires_native
def test_smoke_cli_profile(monkeypatch, tmp_path):
    from generic_chess.learning import diagnostics as diag

    captured = {}

    def fake_run(compiled, native_rules, openings, seed, artifacts_dir, **kwargs):
        captured["seed"] = seed
        captured["artifacts_dir"] = str(artifacts_dir)
        captured.update(kwargs)
        return {"meta": {}, "verdict": {"td_signal": "PRESENT"}, "td_summary": {"n": 1}}

    monkeypatch.setattr(diag, "run_diagnostics", fake_run)

    # --smoke shrinks the profile but respects explicit overrides.
    rc = diag.main(
        [
            "--smoke",
            "--ruleset", "R2_weird_generic",
            "--seed", "7",
            "--artifacts", str(tmp_path),
        ]
    )
    assert rc == 0
    assert captured["seed"] == 7
    assert captured["corpus_count"] == 48
    assert captured["student_nodes"] == 500
    assert captured["teacher_nodes"] == 1500
    assert str(tmp_path) in captured["artifacts_dir"]

    captured.clear()
    rc = diag.main(
        [
            "--smoke",
            "--ruleset", "R2_weird_generic",
            "--seed", "8",
            "--corpus-count", "12",
            "--student-nodes", "80",
            "--teacher-nodes", "200",
            "--artifacts", str(tmp_path / "custom"),
        ]
    )
    assert rc == 0
    assert captured["seed"] == 8
    assert captured["corpus_count"] == 12
    assert captured["student_nodes"] == 80
    assert captured["teacher_nodes"] == 200

    # Default (non-smoke) profile remains the full experiment size.
    captured.clear()
    rc = diag.main(
        [
            "--ruleset", "R2_weird_generic",
            "--seed", "9",
            "--artifacts", str(tmp_path / "full"),
        ]
    )
    assert rc == 0
    assert captured["seed"] == 9
    assert captured["corpus_count"] == 512
    assert captured["student_nodes"] == 4000
    assert captured["teacher_nodes"] == 40000
