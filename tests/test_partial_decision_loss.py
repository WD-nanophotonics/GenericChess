from fractions import Fraction as F
from itertools import product

import pytest

from scripts.partial_decision_loss import (regret_bounds, paired_margin,
                                           classify_regret, certify_population)


def test_known_selected_win_unknown_alternatives_and_singleton():
    assert classify_regret({'a': (1, 1), 'b': (-1, 1)}, 'a')['verdict'] == 'certified_pass'
    assert regret_bounds({'a': (-1, -1), 'b': (0, 1)}, 'a') == (1, 2)
    assert regret_bounds({'a': (-1, 1)}, 'a') == (0, 0)
    assert classify_regret({'a': (-1, 1), 'b': (-1, 1)}, 'a')['verdict'] == 'inconclusive'
    assert classify_regret({'a': (-1, -1), 'b': (0, 1)}, 'a')['verdict'] == 'certified_failure'


def test_complete_interval_boxes_match_independent_regret_oracle():
    pairs = ((-1, -1), (0, 0), (1, 1), (-1, 0), (0, 1), (-1, 1))
    for box in product(pairs, repeat=3):
        intervals = dict(enumerate(box))
        grids = [tuple(F(i, 2) for i in range(2*lo, 2*hi+1)) for lo, hi in box]
        for owner, selected in product((0, 1), range(3)):
            actual = []
            for values in product(*grids):
                values = [v if owner == 0 else -v for v in values]
                actual.append(max(values)-values[selected])
            assert regret_bounds(intervals, selected, owner) == (min(actual), max(actual))
            for baseline in range(3):
                margin = []
                for values in product(*grids):
                    values = [v if owner == 0 else -v for v in values]
                    optimum = max(values)
                    margin.append((optimum-values[baseline])-(optimum-values[selected]))
                assert paired_margin(intervals, selected, baseline, owner) == (min(margin), max(margin))


def test_pairing_cancels_common_unknown_optimum_and_same_choice():
    intervals = {'a': (0, 0), 'b': (-1, -1), 'unknown': (-1, 1)}
    assert regret_bounds(intervals, 'a') == (0, 1)
    assert regret_bounds(intervals, 'b') == (1, 2)
    assert paired_margin(intervals, 'a', 'b') == (1, 1)
    assert paired_margin(intervals, 'unknown', 'unknown') == (0, 0)
    assert paired_margin(intervals, 'a', 'b', 1) == (-1, -1)


def test_population_margin_uses_same_root_and_declared_additive_gate():
    roots = [({'a': (0, 0), 'b': (-1, -1), 'x': (-1, 1)}, 'a', 'b', 0),
             ({'a': (-1, 1)}, 'a', 'a', 1)]
    result = certify_population(roots, [F(1, 2)]*2, F(1, 2))
    assert result['margin'] == (F(1, 2), F(1, 2))
    assert result['verdict'] == 'certified_improvement'
    assert certify_population(roots, [F(1, 2)]*2, F(3, 4))['verdict'] == 'certified_failure'
    unknown = [({'a': (-1, 1), 'b': (-1, 1)}, 'a', 'b', 0)]
    assert certify_population(unknown, [1], F(1, 10))['verdict'] == 'inconclusive'


def test_invalid_intervals_selections_owners_measure_and_margin_fail_closed():
    for intervals, selected, owner in (({}, 'a', 0), ({'a': (1, -1)}, 'a', 0),
          ({'a': (-2, 1)}, 'a', 0), ({'a': (0., 1)}, 'a', 0),
          ({'a': (0, 1)}, 'b', 0), ({'a': (0, 1)}, 'a', True)):
        with pytest.raises(ValueError):
            regret_bounds(intervals, selected, owner)
    root = ({'a': (0, 1)}, 'a', 'a', 0)
    for roots, weights, delta in (([], [], 1), ([root], [F(1, 2)], 1),
          ([root], [1.], 1), ([root], [1], 0), ([root], [1], F(3))):
        with pytest.raises(ValueError):
            certify_population(roots, weights, delta)


def test_score_calibration_not_equivalent_to_choice_quality():
    # Independently recompute dot's arithmetic; no Chess labels or fitted weights.
    true = [F(1), F(0)]
    a, b = [F(10), F(0)], [F(49, 100), F(1, 2)]
    mse = lambda p: sum((x-y)**2 for x, y in zip(p, true))/2
    assert mse(a) == F(81, 2) > mse(b) == F(5101, 20000)
    assert max(range(2), key=a.__getitem__) == 0
    assert max(range(2), key=b.__getitem__) == 1


def test_bounded_observer_intervals_certify_same_root_comparison_soundly():
    from test_public_goal_intervals import Node, TinyGame, leaf, oracle
    from scripts.public_goal_intervals import observe
    for owner, values in product((0, 1), product((-1, 0, 1), repeat=3)):
        children = (Node(1-owner, (leaf(values[0]), leaf(values[1]))),
                    Node(owner, (leaf(values[1]), leaf(values[2]))))
        exact = [oracle(child) for child in children]
        for depth, budget in product(range(3), range(3)):
            intervals = {i: observe(child, TinyGame(), depth=depth,
                                    max_transitions=budget, clock=lambda: 0)['interval']
                         for i, child in enumerate(children)}
            for selected in range(2):
                low, high = regret_bounds(intervals, selected, owner)
                root_values = exact if owner == 0 else [-v for v in exact]
                assert low <= max(root_values)-root_values[selected] <= high
                low, high = paired_margin(intervals, selected, 1-selected, owner)
                assert low <= root_values[selected]-root_values[1-selected] <= high
