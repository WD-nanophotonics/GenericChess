from __future__ import annotations

import numpy as np

from scripts.f125_known_oracle_one_ply_search_compression import (
    DECISION_ROOT_SEEDS,
    FrozenBasis,
    _decision_summary,
    _declaration_present,
    _prepare_filtered,
    _rank_summary,
    _selected_families,
    _teacher_row,
    _t1,
    _t1_from_children,
)
from scripts.f127_shogi_t1_scalar_compression_expanded_control import eligibility_from_children
from scripts.f127_shogi_t1_scalar_compression_expanded_control import _scalar_gate, _search_representation_gate
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
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


def test_shogi_teacher_row_child_reuse_matches_original_formulation_on_32_states():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis("standard_shogi", compiled)
    state = initial_state(compiled)

    for index in range(32):
        actions = sorted(legal_actions(state, compiled), key=str)
        children = [(action, apply_action(state, action, compiled)) for action in actions]
        value, spectrum, terminal_child = _t1_from_children(state, basis, children)
        root_declaration = _declaration_present(state, compiled)
        child_declaration = any(_declaration_present(child, compiled) for _, child in children)
        original = {
            "t1": value,
            "spectrum": spectrum,
            "terminal_child": terminal_child,
            "root_shogi_declaration": root_declaration,
            "child_shogi_declaration": child_declaration,
            "shogi_declaration": root_declaration or child_declaration,
        }
        reused = _teacher_row({"state": state}, basis)

        assert reused["t1"] == original["t1"]
        assert reused["terminal_child"] == original["terminal_child"]
        assert reused["root_shogi_declaration"] == original["root_shogi_declaration"]
        assert reused["child_shogi_declaration"] == original["child_shogi_declaration"]
        assert reused["shogi_declaration"] == original["shogi_declaration"]
        assert [str(action) for action, _ in reused["spectrum"]] == [str(action) for action, _ in original["spectrum"]]
        np.testing.assert_allclose(
            [score for _, score in reused["spectrum"]],
            [score for _, score in original["spectrum"]],
            rtol=0.0,
            atol=0.0,
        )

        if not actions:
            break
        state = children[index % len(children)][1]


def test_f127_eligibility_matches_teacher_exclusion_flags_on_64_shogi_states():
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis("standard_shogi", compiled)
    state = initial_state(compiled)

    for index in range(64):
        actions = sorted(legal_actions(state, compiled), key=str)
        children = [(action, apply_action(state, action, compiled)) for action in actions]
        old = _teacher_row({"state": state}, basis)
        new = eligibility_from_children(state, children, compiled)

        assert new["terminal_child"] == old["terminal_child"]
        assert new["root_shogi_declaration"] == old["root_shogi_declaration"]
        assert new["child_shogi_declaration"] == old["child_shogi_declaration"]
        assert (new["root_shogi_declaration"] or new["child_shogi_declaration"]) == old["shogi_declaration"]

        if not actions:
            break
        state = children[index % len(children)][1]


def test_f127_search_representation_gate_is_distinct_from_direct_control_gate():
    metrics = {"holdout": {"normalized_rmse": 0.10, "r2": 0.97, "pearson": 0.98}}

    assert _scalar_gate(metrics)["pass"] is False
    assert _search_representation_gate(metrics)["pass"] is True
