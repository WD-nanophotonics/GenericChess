"""Contracts for the F63-R2 strength-first cheap funnel."""

import inspect

import pytest

from scripts import f63_r2_strength_first_cheap_funnel as funnel


def test_new_namespace_and_frozen_population_are_explicit():
    assert funnel.WORK_ORDER == "GENERICCHESS-F63-R2-STRENGTH-FIRST-CHEAP-FUNNEL"
    assert funnel.PARENT_SHA == "0a109224311c625a635d3ecdc58e63b2a04e5586"
    assert funnel.GEN1_ID == "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
    assert funnel.CANDIDATE_SEEDS == (59011, 59012, 59013)
    assert "f63-r2-strength-first-cheap-funnel" in str(funnel.OUT)
    assert funnel.STAGE0_ROOTS_PER_DISTRIBUTION == 1


def test_old_r10_evidence_is_never_selection_input(monkeypatch, tmp_path):
    monkeypatch.setattr(funnel.f63, "PROGRESS", tmp_path)
    (tmp_path / "candidate-59011-common-4-calibrated-seed-630403").mkdir()
    (tmp_path / "candidate-59012-common-4-calibrated-seed-630403").mkdir()
    for index in range(8):
        (tmp_path / "candidate-59011-common-4-calibrated-seed-630403" / f"game-{index:06d}.json").write_text("{}")
    for index in range(6):
        (tmp_path / "candidate-59012-common-4-calibrated-seed-630403" / f"game-{index:06d}.json").write_text("{}")
    status = funnel.historical_r10_status()
    assert status["classification"] == "R10_COMMON4_USER_STOPPED_UNEQUAL_EXPOSURE"
    assert status["comparable"] is False
    assert status["selection_authority"] == "forbidden"


def test_proxy_metrics_cannot_be_hard_gates():
    assert funnel.stage0_proxy_is_diagnostic("teacher_agreement")
    assert funnel.stage0_proxy_is_diagnostic("action_regret")
    assert not funnel.stage0_hard_fail(correctness_violation=False)
    assert funnel.stage0_hard_fail(correctness_violation=True)


def test_short64_truncation_is_unresolved_and_pair_scores_require_completion():
    assert funnel.short64_outcome(complete=False) == {
        "status": "UNRESOLVED", "score": None, "winner": None
    }
    assert funnel.pair_score(complete=False, child_score=1.0) is None
    assert funnel.pair_score(complete=True, child_score=0.5) == 0.5


def test_later_strength_gates_are_conservative():
    assert funnel.stage2_survives(0.5)
    assert not funnel.stage2_survives(0.499)
    assert funnel.stage3_positive(0.75, 2, 0)
    assert not funnel.stage3_positive(0.75, 1, 1)
    assert not funnel.stage4_requires_complete(7)
    assert funnel.stage4_requires_complete(8)


def test_stage_entry_points_are_separate_and_no_aggregate_runner_exists():
    assert funnel.STAGE_NAMES == ("screen", "short64", "arena2", "arena4", "arena8")
    source = inspect.getsource(funnel.main)
    assert "run_screen" in source
    assert "run_short64" in source
    assert "run_arena8" in source
    assert not hasattr(funnel, "run_all")


@pytest.mark.parametrize("name", ["run_short64", "run_arena2", "run_arena4", "run_arena8"])
def test_later_stages_require_reviewed_prerequisites(name):
    with pytest.raises(RuntimeError, match="separate reviewed work-order boundary"):
        getattr(funnel, name)()
