from __future__ import annotations

from fractions import Fraction

import pytest

from scripts.audit_static_material_v2h_rule_support_source_prior import (
    _conditional_mean,
    _reachable_nodes,
    audit,
)


def test_rule_support_reachability_is_seeded_and_directed_across_type_changes() -> None:
    graph = {
        ("P", 0): {("P", 1), ("Q", 2)},
        ("P", 1): set(),
        ("Q", 2): {("Q", 3)},
        ("Q", 3): set(),
        ("R", 4): set(),
    }
    assert _reachable_nodes(graph, {("P", 0)}) == {
        ("P", 0), ("P", 1), ("Q", 2), ("Q", 3),
    }
    assert _reachable_nodes(graph, {("R", 4)}) == {("R", 4)}


def test_conditional_mean_is_exact_and_rejects_invalid_support() -> None:
    values = [Fraction(1), Fraction(2), Fraction(100)]
    assert _conditional_mean(values, [0, 1]) == Fraction(3, 2)
    with pytest.raises(RuntimeError):
        _conditional_mean(values, [])
    with pytest.raises(RuntimeError):
        _conditional_mean(values, [0, 0])


def test_complete_pre_reference_candidate_reconstructs_full_and_restricted_types() -> None:
    candidate = audit()
    assert candidate["classification"] == "STATIC_MATERIAL_RULE_SUPPORT_CONDITIONED_SOURCE_PRIOR_COMPLETE"
    assert candidate["human_reference_imported"] is False
    assert candidate["human_validation_performed"] is False
    assert candidate["games_played"] == 0
    assert candidate["coverage_complete"] is True
    assert candidate["reconstruction_complete"] is True
    assert candidate["support_gates_pass"] is True
    assert candidate["rulesets"]["western_chess"]["types"]["P"]["b_support_exact"] == "23945/13392"
    assert candidate["rulesets"]["standard_shogi"]["types"]["L"]["b_support_exact"] == "19728450347/5917542400"
    assert candidate["rulesets"]["standard_shogi"]["types"]["N"]["b_support_exact"] == "2519/1260"
    assert candidate["rulesets"]["standard_shogi"]["types"]["P"]["b_support_exact"] == "1559/1280"
    for ruleset in candidate["rulesets"].values():
        for row in ruleset["types"].values():
            assert row["component_sum_exact"] is True
            assert row["source_coverage_complete"] is True
            if not row["restricted_support"]:
                assert row["full_support_reproduces_v2d"] is True
