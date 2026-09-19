from __future__ import annotations

import numpy as np

from scripts.f125_known_oracle_one_ply_search_compression import (
    DECISION_ROOT_SEEDS,
    _decision_summary,
    _prepare_filtered,
    _rank_summary,
    _selected_families,
    _t1,
    _t1_from_children,
)
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def test_rank_summary_uses_stable_reference_ties_and_regret():
    summary = _rank_summary([1.0, 0.5, 0.5], [0.5, 1.0, 0.5])

    assert summary["top"] == 0
    assert summary["top1"] is False
    assert summary["regret"] == 0.5
    assert 0.0 <= summary["pairwise"] <= 1.0


def test_decision_summary_separates_search_disagreements_from_retention():
    records = [
        {"static": {"top1": True, "regret": 0.0}, "compressed": {"top1": True, "pairwise": 1.0, "regret": 0.0, "top2_gap": 1.0}, "depth2_scores": [2.0, 1.0]},
        {"static": {"top1": False, "regret": 1.0}, "compressed": {"top1": True, "pairwise": 1.0, "regret": 0.0, "top2_gap": 1.0}, "depth2_scores": [1.0, 2.0]},
    ]
    summary = _decision_summary(records)

    assert summary["informative"] == 1
    assert summary["teacher_disagreement_recovery"]["recovery"] == 1.0
    assert summary["teacher_correct_retention"]["retention"] == 1.0


def test_filtered_preparation_normalizes_each_retained_split_from_train_only():
    class Basis:
        names = ["x"]

    rows = [
        {"features": [0.0], "split": "train"},
        {"features": [2.0], "split": "train"},
        {"features": [4.0], "split": "dev"},
        {"features": [6.0], "split": "holdout"},
    ]
    pack = _prepare_filtered(rows, [0.0, 2.0, 4.0, 6.0], Basis())

    np.testing.assert_allclose(pack["feature_mean"], [1.0])
    np.testing.assert_allclose(pack["feature_scale"], [1.0])
    assert pack["design"]["train"].shape == (2, 2)
    assert pack["design"]["holdout"].shape == (1, 2)


def test_selected_families_supports_independent_family_runs():
    selected = _selected_families("western_chess")

    assert [family for family, _, _, _ in selected] == ["western_chess"]
    assert DECISION_ROOT_SEEDS["western_chess"] == 1250121


def test_child_reuse_preserves_one_ply_teacher():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    state = initial_state(compiled)

    class Basis:
        family = "western_chess"

        @staticmethod
        def vector(_state):
            return np.zeros(1)

        @staticmethod
        def oracle(_vector):
            return 0.0

    Basis.compiled = compiled
    actions = sorted(legal_actions(state, compiled), key=str)
    children = [(action, apply_action(state, action, compiled)) for action in actions]

    assert _t1(state, Basis()) == _t1_from_children(state, Basis(), children)
