"""Synthetic frozen-receipt algebra, not new episodes, search or fitting."""
from math import tanh
import pytest
from generic_chess.learning.incremental import Model
from scripts.verify_leaper_ab_learning import td_sum

BEFORE = [1., 1., 1.]
RECEIPTS = [dict(value=0., pv_phi=(0., 1., -1.), pv_terminal=False),
            dict(value=1., pv_phi=(0., 2., -1.), pv_terminal=False)]


def test_final_target_family_is_affine_but_none_is_not_draw():
    lo = td_sum(BEFORE, RECEIPTS, -1.)[0]
    zero = td_sum(BEFORE, RECEIPTS, 0.)[0]
    hi = td_sum(BEFORE, RECEIPTS, 1.)[0]
    missing, stats = td_sum(BEFORE, RECEIPTS, None)
    assert zero == pytest.approx([(a + b) / 2 for a, b in zip(lo, hi)], abs=1e-15)
    assert missing != zero
    assert stats['samples'] == 1 and stats['censored']
    # This is a hypothetical REAL target equal to the last bootstrap value,
    # not a permitted actual deterministic WDL outcome passed to the learner.
    bootstrapped = td_sum(BEFORE, RECEIPTS, tanh(.1))[0]
    assert missing == pytest.approx(bootstrapped, abs=1e-15)
    for z in (-.75, -.2, .3, .9):
        actual = td_sum(BEFORE, RECEIPTS, z)[0]
        t = (z + 1) / 2
        assert actual == pytest.approx([(1 - t) * a + t * b for a, b in zip(lo, hi)], abs=1e-15)


def test_coordinate_box_corners_are_not_independent_outcome_completions():
    lo = td_sum(BEFORE, RECEIPTS, -1.)[0]
    hi = td_sum(BEFORE, RECEIPTS, 1.)[0]
    assert lo[1] < hi[1] and lo[2] > hi[2]
    impossible_both_max = [1., hi[1], lo[2]]
    for z in (-1., 0., 1.):
        assert td_sum(BEFORE, RECEIPTS, z)[0] != impossible_both_max
    # One outcome z simultaneously controls every coordinate; z=+1 is needed
    # for the largest second weight, while z=-1 is needed for the third.


def test_lambda_one_none_retains_bootstrap_target_instead_of_monte_carlo_draw():
    missing, _ = td_sum(BEFORE, RECEIPTS, None, lam=1.)
    draw, _ = td_sum(BEFORE, RECEIPTS, 0., lam=1.)
    last_bootstrap, _ = td_sum(BEFORE, RECEIPTS, tanh(.1), lam=1.)
    assert missing != draw
    assert missing == pytest.approx(last_bootstrap, abs=1e-15)


def test_tied_pv_gradient_need_not_descend_restricted_minimax_prediction_loss():
    # Two synthetic leaf features. Their rule reachability is NOT asserted.
    # This isolates the exact min-of-material-functions calculus at a tie.
    phi_plus, phi_minus = (-1., 1.), (1., -1.)
    model = Model([1., 1.], scale=10.)
    assert model.raw(phi_plus) == model.raw(phi_minus) == 0
    assert model.gradient(phi_plus)[1] == .1
    assert model.gradient(phi_minus)[1] == -.1
    scores = lambda m: [m.prediction(phi) for phi in (phi_plus, phi_minus)]
    old_min, old_max = min(scores(model)), max(scores(model))
    # Reuse independent arithmetic for a single hypothetical +1 final target.
    after, _ = td_sum([1., 1.], [dict(value=0., pv_phi=phi_plus, pv_terminal=False)], 1.)
    new_model = Model(after, scale=10.)
    assert after == [1., 1.005]
    assert .5 * (min(scores(new_model)) - 1) ** 2 > .5 * (old_min - 1) ** 2
    assert .5 * (max(scores(new_model)) - 1) ** 2 < .5 * (old_max - 1) ** 2
    assert model.weights == [1., 1.]  # No parameter update on this object.


def test_unique_leaf_gradient_matches_fixed_tree_finite_difference():
    phi_plus, phi_minus = (-1., 1.), (1., -1.)
    weight = 1.2
    model = Model([1., weight], scale=10.)
    chosen_phi = phi_minus  # Unique min when B>A.
    eps = 1e-6
    f = lambda b: min(Model([1., b], scale=10.).prediction(phi) for phi in (phi_plus, phi_minus))
    numerical = (f(weight + eps) - f(weight - eps)) / (2 * eps)
    assert model.gradient(chosen_phi)[1] == pytest.approx(numerical, rel=1e-8)
    # The unique-PV derivative argument is local to a fixed complete tree; no
    # claim is made for budget-dependent/cancelled adaptive search trees.



def test_final_eligibility_cancellation_can_remove_outcome_sensitivity_only():
    receipts = [dict(value=1., pv_phi=(0., 1.), pv_terminal=False),
                dict(value=-1., pv_phi=(0., -1.), pv_terminal=False)]
    values = [td_sum([1., 1.], receipts, z, lam=1.)[0] for z in (-1., 0., 1., None)]
    assert all(v == values[0] for v in values)
    assert values[0][1] != 1.  # The already observed interior term still matters.
    assert values[0][0] == 1.  # The declared physical unit remains fixed.



def test_tied_selected_gradient_can_miss_an_available_improving_direction():
    # Three synthetic material channels, no claim of a legal source position.
    # Unlike the two-channel cusp example, a joint improving direction exists.
    phis = ((-1., 1., 0.), (-1., -1., 2.))
    before = [1., 1., 1.]
    old = Model(before, scale=10.)
    assert [old.raw(phi) for phi in phis] == [0., 0.]
    selected, _ = td_sum(before, [dict(value=0., pv_phi=phis[0], pv_terminal=False)], 1.)
    selected_model = Model(selected, scale=10.)
    joint_model = Model([1., 1.005, 1.005], scale=10.)
    restricted_loss = lambda m: .5 * (min(m.prediction(phi) for phi in phis) - 1) ** 2
    assert restricted_loss(selected_model) > restricted_loss(old)
    assert restricted_loss(joint_model) < restricted_loss(old)
    assert old.weights == before
