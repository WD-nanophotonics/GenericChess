from fractions import Fraction as F
import pytest
from scripts.audit_exposed_inventory_preferences import oriented_difference, preference_status


def test_both_owner_score_order_matches_direct_independent_evaluation():
    first = {'R': -1, 'B': 2}; second = {'R': 1, 'B': -1}
    for owner in (0, 1):
        for r in (0, F(1, 3), 1):
            for b in (0, F(2, 3), 1):
                w = {'R': r, 'B': b}
                actual = (sum(first[k]*w[k] for k in w)-sum(second[k]*w[k] for k in w))*(1 if owner == 0 else -1)
                result = preference_status(oriented_difference(first, second, owner), w, 'b', 'a')
                assert result['oriented_score_margin'] == actual
                assert result['pair_selects_preferred'] == (actual > 0)


def test_zero_difference_is_strict_obstruction_but_not_all_tie_choices():
    d = oriented_difference({'R': 1}, {'R': 1}, 0)
    assert d == {}
    good = preference_status(d, {}, 'a', 'b')
    bad = preference_status(d, {}, 'b', 'a')
    assert not good['strict_score_represented'] and good['pair_selects_preferred']
    assert not bad['pair_selects_preferred']


def test_opposite_constraints_can_be_weakly_tied_not_strictly_met():
    for w in range(3):
        positive = preference_status({'R': 1}, {'R': w}, 'a', 'b')
        negative = preference_status({'R': -1}, {'R': w}, 'a', 'b')
        assert not (positive['strict_score_represented'] and negative['strict_score_represented'])
        assert (positive['pair_selects_preferred'] and negative['pair_selects_preferred']) == (w == 0)


def test_missing_or_inexact_weight_fails():
    with pytest.raises(ValueError, match='missing'):
        preference_status({'R': 1}, {}, 'a', 'b')
    with pytest.raises(ValueError, match='exact'):
        preference_status({'R': 1}, {'R': .5}, 'a', 'b')
