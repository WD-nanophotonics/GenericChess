from fractions import Fraction as F
import pytest
from scripts.audit_two_victim_direct_intervals import aggregate, TYPES


def roots():
    return [{'type': t, 'first_complete': False} for t in TYPES for _ in range(24)]


def test_fixed_population_contains_independent_exact_worlds_for_every_prefix():
    # An independently defined240-event law: each root has two equally likely
    # reward outcomes. A prefix observes roots, not a replacement population.
    exact = [(F(i % 3, 3), F((i % 5), 5)) for i in range(24)]
    target = sum(a+b for a, b in exact)/24
    for visited in range(25):
        rows = roots()
        for row, (a, b) in zip(rows[:visited], exact):
            row.update(first_complete=True, first_mean=a, future_interval=(b, b))
        result = aggregate(rows)
        lo, hi = result['P']['raw_interval']
        assert lo <= target <= hi
        assert hi-lo == F(2*(24-visited), 24)
        assert result['N']['raw_interval'] == (F(0), F(2))
        if visited == 24:
            assert lo == hi == target


def test_incomplete_first_numerator_does_not_become_a_zero_reward():
    rows = roots()
    for row in rows:
        row.update(first_mean=F(0), future_interval=(F(0), F(0)))
    assert all(r['raw_interval'] == (F(0), F(2)) for r in aggregate(rows).values())


def test_exact_first_and_partial_future_preserve_common_gauge():
    rows = roots()
    for i, row in enumerate(rows):
        row.update(first_complete=True, first_mean=F(i % 2),
                   future_interval=(F(1, 4), F(3, 4)))
    assert all(r['raw_interval'] == (F(3, 4), F(5, 4)) and
               r['common_scaled_interval'] == (F(3, 8), F(5, 8))
               for r in aggregate(rows).values())


def test_missing_root_mass_is_an_error():
    with pytest.raises(ValueError, match='24 roots'):
        aggregate(roots()[:-1])
