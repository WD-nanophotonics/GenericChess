from fractions import Fraction as F
from itertools import product
import pytest
from scripts.public_task_intervals import (
    integrate_public_action, public_choice_bound, completion_custody_probability,
)


def test_hidden_assignment_is_integrated_before_public_optimization():
    q = {'board_tag': F(1, 2), 'held_tag': F(1, 2)}
    payoffs = ({'board_tag': (1, 1), 'held_tag': (0, 0)},
               {'board_tag': (0, 0), 'held_tag': (1, 1)})
    actions = {i: integrate_public_action(q, p) for i, p in enumerate(payoffs)}
    assert public_choice_bound(actions, maximize=True, complete=True) == (F(1, 2), F(1, 2))
    clairvoyant = sum(q[k]*max(p[k][0] for p in payoffs) for k in q)
    assert clairvoyant == 1
    assert public_choice_bound(actions, maximize=False, complete=True) == (F(1, 2), F(1, 2))


def test_joint_completion_and_survival_cannot_be_replaced_by_product():
    # Capturing actor is the tag in half the physical worlds, but that actor
    # is then removed; the surviving hand-tag worlds never completed the task.
    q = {(True, False): F(1, 2), (False, True): F(1, 2)}
    assert completion_custody_probability(q) == 0
    assert sum(p for (c, _), p in q.items() if c)*sum(p for (_, a), p in q.items() if a) == F(1, 4)


def test_bounds_contain_independent_hidden_world_and_missing_action_enumeration():
    pairs = ((F(0), F(1, 2)), (F(1, 2), F(1)), (F(0), F(1)))
    q = {'w0': F(1, 3), 'w1': F(2, 3)}
    for p0, p1 in product(pairs, repeat=2):
        observed = {'a': integrate_public_action(q, {'w0': p0, 'w1': p1})}
        for maximize in (False, True):
            lo, hi = public_choice_bound(observed, maximize=maximize, complete=False)
            for v0, v1, missing in product(p0, p1, (0, 1)):
                known = q['w0']*v0+q['w1']*v1
                actual = (max if maximize else min)(known, missing)
                assert lo <= actual <= hi


def test_optional_action_monotonicity_and_range_dominance_do_not_claim_tie():
    base = {'a': (F(1), F(1))}; extra = {**base, 'b': (0, 0)}
    assert public_choice_bound(base, maximize=True, complete=True) == (F(1), F(1))
    assert public_choice_bound(extra, maximize=True, complete=True) == (F(1), F(1))
    assert sum(p[0] for p in extra.values())/len(extra) == F(1, 2)
    assert public_choice_bound(base, maximize=True, complete=False) == (F(1), F(1))
    assert public_choice_bound({'a': (0, 0)}, maximize=False, complete=False) == (F(0), F(0))
    assert public_choice_bound({}, maximize=False, complete=False) == (F(0), F(1))


def test_missing_world_mass_or_inexact_probabilities_fail_closed():
    with pytest.raises(ValueError, match='support'):
        integrate_public_action({'a': F(1, 2), 'b': F(1, 2)}, {'a': (0, 1)})
    with pytest.raises(ValueError, match='sum'):
        integrate_public_action({'a': F(1, 2)}, {'a': (0, 1)})
    with pytest.raises(ValueError, match='exact'):
        integrate_public_action({'a': 1.0}, {'a': (0, 1)})
    with pytest.raises(ValueError, match='nonempty'):
        public_choice_bound({}, maximize=True, complete=True)
