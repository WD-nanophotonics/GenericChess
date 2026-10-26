"""Exhaustive arithmetic controls; no game computation or parameter updates."""
from itertools import product
from math import isclose
import pytest
from generic_chess.learning.incremental import Model
from scripts.interval_value_diagnostics import (
    actor_view, loss_envelope, paired_loss_difference, weighted_outer_summary,
)

BOUNDS = tuple((lo, hi) for lo in (-1, 0, 1) for hi in (-1, 0, 1) if lo <= hi)
GRID = tuple(i / 10 for i in range(-10, 11))


def test_exhaustive_discrete_errors_and_shared_truth_difference():
    # Independent enumerate every permitted true WDL, not another interval formula.
    for bounds, a, b in product(BOUNDS, GRID, GRID):
        truth = [v for v in (-1, 0, 1) if bounds[0] <= v <= bounds[1]]
        errors = [(a - v) ** 2 for v in truth]
        diffs = [(a - v) ** 2 - (b - v) ** 2 for v in truth]
        risk, pair = loss_envelope(a, bounds), paired_loss_difference(a, b, bounds)
        from fractions import Fraction
        exact_errors = [(Fraction(a) - v) ** 2 for v in truth]
        assert Fraction(risk['deterministic_WDL_lower']) <= min(exact_errors)
        assert Fraction(risk['squared_error_upper']) >= max(exact_errors)
        assert risk['deterministic_WDL_lower'] == pytest.approx(min(errors), abs=1e-14)
        assert risk['squared_error_upper'] == pytest.approx(max(errors), abs=1e-14)
        assert risk['continuous_relaxation_lower'] <= min(errors) + 1e-14
        assert pair['lower'] == pytest.approx(min(diffs), abs=1e-14)
        assert pair['upper'] == pytest.approx(max(diffs), abs=1e-14)


def test_unknown_is_no_continuous_constraint_but_not_known_zero_error():
    r = loss_envelope(.4, [-1, 1])
    assert r['continuous_constraint_derivative'] == 0
    assert r['continuous_relaxation_lower'] == 0
    assert r['deterministic_WDL_lower'] == pytest.approx(.16)
    assert r['squared_error_upper'] == pytest.approx(1.96)
    assert r['point_target_derivative_bounds'] == pytest.approx((-1.2, 2.8))
    # Choosing the nearest WDL here would invent a preferred truth of zero.
    assert r['feasible_WDL'] == (-1, 0, 1)


def test_one_sided_bound_does_not_select_midpoint_or_endpoint():
    r = loss_envelope(.4, [0, 1])
    assert r['continuous_constraint_derivative'] == 0
    assert r['deterministic_WDL_lower'] == pytest.approx(.16)
    assert r['squared_error_upper'] == pytest.approx(.36)
    assert r['feasible_WDL'] == (0, 1)
    assert 'target' not in r


def test_paired_difference_can_certify_when_independent_errors_overlap():
    a, b, bounds = -.1, -.9, [0, 1]
    ar, br = loss_envelope(a, bounds), loss_envelope(b, bounds)
    assert ar['squared_error_upper'] > br['deterministic_WDL_lower']
    pair = paired_loss_difference(a, b, bounds)
    assert pair['verdict'] == 'A_STRICTLY_LOWER_SCALAR_ERROR'
    assert pair['lower'] == pytest.approx(-2.4)
    assert pair['upper'] == pytest.approx(-.8)


def test_sign_and_endpoint_conversion_preserves_risk_and_pair():
    for bounds, a, b in product(BOUNDS, GRID, GRID):
        av, actor_bounds = actor_view(a, bounds, 1)
        bv, _ = actor_view(b, bounds, 1)
        for key in ('continuous_relaxation_lower', 'deterministic_WDL_lower', 'squared_error_upper'):
            assert loss_envelope(av, actor_bounds)[key] == loss_envelope(a, bounds)[key]
        actor_pair = paired_loss_difference(av, bv, actor_bounds)
        base_pair = paired_loss_difference(a, b, bounds)
        assert actor_pair == base_pair


def test_constraint_derivative_and_actual_model_chain_rule_without_update():
    model = Model([1., .5], scale=2.)
    phi = (0., -1.)
    p = model.prediction(phi)
    r = loss_envelope(p, [0, 1])
    grad = model.gradient(phi)
    analytic = r['continuous_constraint_derivative'] * grad[1]
    eps = 1e-6
    plus = Model([1., .5 + eps], scale=2.)
    minus = Model([1., .5 - eps], scale=2.)
    numerical = (loss_envelope(plus.prediction(phi), [0, 1])['continuous_relaxation_lower'] -
                 loss_envelope(minus.prediction(phi), [0, 1])['continuous_relaxation_lower']) / (2 * eps)
    assert analytic == pytest.approx(numerical, rel=1e-8)
    assert model.weights == [1., .5]
    assert grad[0] == 0


def test_aggregate_bounds_contain_every_rectangular_completion():
    rows = [(1., .2, -.4, [0, 1]), (2., -.1, .3, [-1, 0])]
    summary = weighted_outer_summary(rows)
    for truth in product((0, 1), (-1, 0)):
        a = sum(w * (pa - v) ** 2 for (w, pa, pb, _), v in zip(rows, truth)) / 3
        b = sum(w * (pb - v) ** 2 for (w, pa, pb, _), v in zip(rows, truth)) / 3
        assert summary['a_lower'] - 1e-14 <= a <= summary['a_upper'] + 1e-14
        assert summary['b_lower'] - 1e-14 <= b <= summary['b_upper'] + 1e-14
        assert summary['paired_lower'] - 1e-14 <= a - b <= summary['paired_upper'] + 1e-14
    split = weighted_outer_summary([rows[0], (1., -.1, .3, [-1, 0]), (1., -.1, .3, [-1, 0])])
    for key in ('a_lower', 'a_upper', 'b_lower', 'b_upper', 'paired_lower', 'paired_upper'):
        assert split[key] == pytest.approx(summary[key])


@pytest.mark.parametrize('prediction,bounds', [(float('nan'), [-1, 1]), (float('inf'), [0, 1]),
    (2., [-1, 1]), (True, [-1, 1]), (0., [1, 0]), (0., [-.5, .5]), (0., [False, 1])])
def test_invalid_score_or_truth_domain_refused(prediction, bounds):
    with pytest.raises(ValueError): loss_envelope(prediction, bounds)


@pytest.mark.parametrize('rows', [[], [(0., 0., 0., [-1, 1])], [(-1., 0., 0., [-1, 1])],
    [(float('inf'), 0., 0., [-1, 1])]])
def test_invalid_aggregate_weight_refused(rows):
    with pytest.raises(ValueError): weighted_outer_summary(rows)


def test_shared_features_constraint_descent_need_not_reduce_true_joint_error():
    # Synthetic compatible truths: first interval[0,1] contains1, second[-1,0]
    # contains0. Both histories alias to the same scalar feature prediction.
    # This is an arithmetic counterexample, not a fitting or update experiment.
    before, after = .5, .49
    intervals = ([0, 1], [-1, 0])
    constraint = lambda p: sum(loss_envelope(p, b)['continuous_relaxation_lower'] for b in intervals) / 2
    true_error = lambda p: ((p - 1) ** 2 + p ** 2) / 2
    derivative = sum(loss_envelope(before, b)['continuous_constraint_derivative'] for b in intervals) / 2
    assert derivative > 0  # Its negative step moves the shared prediction down.
    assert constraint(after) < constraint(before)
    assert true_error(after) > true_error(before)


def test_minimax_upper_loss_imposes_unknown_zero_prior_without_truth():
    # Minimizing worst-case error is a declared decision criterion, not a label.
    assert loss_envelope(0., [-1, 1])['squared_error_upper'] < loss_envelope(.2, [-1, 1])['squared_error_upper']
    # With one-sided[0,1], the minimax compromise is .5, not an actual WDL truth.
    half = loss_envelope(.5, [0, 1])
    assert half['squared_error_upper'] < loss_envelope(0., [0, 1])['squared_error_upper']
    assert .5 not in half['feasible_WDL']


def test_coupled_state_values_make_sum_of_separate_minima_only_outer():
    # A parent with one forced action has the SAME value as its child. Each
    # scalar predictor has optimistic error0 separately at an allowed WDL.
    # Their preferred completions(-1,+1) cannot both be the true shared value.
    rows = [(1., -1., 0., [-1, 1]), (1., 1., 0., [-1, 1])]
    outer = weighted_outer_summary(rows)
    realizable_errors = [((-1 - v) ** 2 + (1 - v) ** 2) / 2 for v in (-1, 0, 1)]
    assert outer['a_lower'] == 0
    assert min(realizable_errors) == 1
    assert outer['a_lower'] < min(realizable_errors) <= outer['a_upper']



def test_choice_regret_difference_matches_exhaustive_values_without_root_truth():
    from scripts.interval_value_diagnostics import choice_regret_difference
    for bounds_a, bounds_b, actor in product(BOUNDS, BOUNDS, (0, 1)):
        report = choice_regret_difference([bounds_a, bounds_b], 0, 1, actor=actor)
        feasible_a = [v for v in (-1, 0, 1) if bounds_a[0] <= v <= bounds_a[1]]
        feasible_b = [v for v in (-1, 0, 1) if bounds_b[0] <= v <= bounds_b[1]]
        differences = []
        # Add a completely unknown third legal option; cancellation must not
        # depend on it or on whether either selected action is globally optimal.
        for va, vb, other in product(feasible_a, feasible_b, (-1, 0, 1)):
            sign = 1 if actor == 0 else -1
            best = max(sign * v for v in (va, vb, other))
            ra, rb = best - sign * va, best - sign * vb
            differences.append(ra - rb)
        assert report['lower'] == min(differences)
        assert report['upper'] == max(differences)


def test_identical_selected_action_regret_difference_is_exact_zero():
    from scripts.interval_value_diagnostics import choice_regret_difference
    for bounds in BOUNDS:
        r = choice_regret_difference([bounds], 0, 0, actor=1)
        assert (r['lower'], r['upper']) == (0., 0.)


def test_partial_pair_can_order_regret_without_complete_frontier_or_root_value():
    from scripts.interval_value_diagnostics import choice_regret_difference
    # Actor0: A DRAW, B LOSS. Unknown omitted alternatives cannot change the
    # shared regret difference of -1. This does not identify the root value.
    r = choice_regret_difference([[0, 0], [-1, -1]], 0, 1, actor=0)
    assert (r['lower'], r['upper']) == (-1., -1.)
    # Seat1 has the opposite preference under the same fixed-seat0 values.
    r = choice_regret_difference([[0, 0], [-1, -1]], 0, 1, actor=1)
    assert (r['lower'], r['upper']) == (1., 1.)


@pytest.mark.parametrize('values,a,b,actor', [([], 0, 0, 0), ([[0, 1]], -1, 0, 0),
    ([[0, 1]], 0, 1, 0), ([[0, 1]], True, 0, 0), ([[0, 1]], 0, 0, True)])
def test_invalid_choice_contrast_is_refused(values, a, b, actor):
    from scripts.interval_value_diagnostics import choice_regret_difference
    with pytest.raises(ValueError): choice_regret_difference(values, a, b, actor=actor)



def test_fully_unknown_row_cannot_strictly_order_bounded_point_predictions():
    # This is an identification limit, not a claim that their errors are equal.
    for a, b in product(GRID, GRID):
        d = paired_loss_difference(a, b, [-1, 1])
        assert d['lower'] <= 0 <= d['upper']
        assert d['upper'] - d['lower'] == pytest.approx(4 * abs(a - b), abs=1e-14)


def test_sparse_certificates_can_order_shared_prediction_pair_without_full_truth():
    # Only1%qualified target mass, but identical predictions on unknown rows
    # cancel. This is a synthetic fixed-row risk comparison, not policy gain.
    rows = [(1., -.1, -.9, [0, 1]), (99., .4, .4, [-1, 1])]
    r = weighted_outer_summary(rows)
    assert r['paired_lower'] == pytest.approx(-.024)
    assert r['paired_upper'] == pytest.approx(-.008)
    assert r['paired_upper'] < 0
    assert r['a_upper'] > r['b_lower']  # Separate risk envelopes still overlap.



def test_actual_large_scale_model_error_underflow_is_not_false_equality():
    from fractions import Fraction
    p = Model([1., 1.], scale=1e200).prediction((0., 1.))
    assert p > 0 and p * p == 0.  # Ordinary float multiplication underflows.
    risk = loss_envelope(p, [0, 0])
    assert risk['squared_error_upper'] > 0
    pair = paired_loss_difference(0., p, [0, 0])
    assert pair['verdict'] == 'A_STRICTLY_LOWER_SCALAR_ERROR'
    assert Fraction(pair['exact_upper']) < 0
    aggregate = weighted_outer_summary([(1., 0., p, [0, 0])])
    assert aggregate['paired_verdict'] == 'A_STRICTLY_LOWER_SCALAR_ERROR'



def test_weighted_outward_bounds_and_exact_pair_survive_tiny_effect_cancellation():
    from fractions import Fraction
    # Independent direct squared-loss enumeration at each permissible truth.
    # The tiny known-row difference disappears if independent float risks are
    # subtracted, but common unknown-row risk must cancel exactly.
    rows = [(.1, 0., 1e-200, [0, 0]), (.3, .4, .4, [-1, 1])]
    report = weighted_outer_summary(rows)
    total = sum(Fraction(r[0]) for r in rows)
    assert report['paired_verdict'] == 'A_STRICTLY_LOWER_SCALAR_ERROR'
    for unknown_value in (-1, 0, 1):
        values = (0, unknown_value)
        a = sum(Fraction(w) * (Fraction(pa) - v) ** 2
                for (w, pa, pb, _), v in zip(rows, values)) / total
        b = sum(Fraction(w) * (Fraction(pb) - v) ** 2
                for (w, pa, pb, _), v in zip(rows, values)) / total
        assert a < b
        assert Fraction(report['a_lower']) <= a <= Fraction(report['a_upper'])
        assert Fraction(report['b_lower']) <= b <= Fraction(report['b_upper'])
        assert Fraction(report['paired_lower']) <= a - b <= Fraction(report['paired_upper'])



def test_pointwise_better_value_errors_can_still_choose_worse_action():
    # Synthetic complete action-value table, not a new rule/game observation.
    # Both bounded candidate estimates are closer to their own true values,
    # yet candidate order reverses the two actions and incurs minimax regret.
    from scripts.interval_value_diagnostics import choice_regret_difference
    baseline = (-.9, .1)
    candidate = (.4, .3)
    truth = (0, 1)
    for a, b, v in zip(candidate, baseline, truth):
        assert paired_loss_difference(a, b, [v, v])['verdict'] == 'A_STRICTLY_LOWER_SCALAR_ERROR'
    baseline_choice = max(range(2), key=lambda i: baseline[i])
    candidate_choice = max(range(2), key=lambda i: candidate[i])
    assert baseline_choice == 1 and candidate_choice == 0
    d = choice_regret_difference([[0, 0], [1, 1]], candidate_choice, baseline_choice, actor=0)
    assert (d['lower'], d['upper']) == (1., 1.)
