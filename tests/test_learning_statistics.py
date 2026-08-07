"""Learning Phase 1.5: pair-level bootstrap statistics."""

import pytest

from generic_chess.learning.statistics import bootstrap_pair_mean_ci


def test_mean_and_determinism():
    scores = [0.0, 0.5, 1.0]
    a = bootstrap_pair_mean_ci(scores)
    b = bootstrap_pair_mean_ci(scores)
    assert a == b
    lo, hi = a
    assert 0.0 <= lo <= 0.5 <= hi <= 1.0
    assert sum(scores) / len(scores) == 0.5


def test_all_ties_ci_is_exact():
    lo, hi = bootstrap_pair_mean_ci([0.5, 0.5, 0.5])
    assert lo == 0.5
    assert hi == 0.5


def test_all_wins_ci_is_exact():
    lo, hi = bootstrap_pair_mean_ci([1.0, 1.0, 1.0])
    assert lo == 1.0
    assert hi == 1.0


def test_empty_rejected():
    with pytest.raises(ValueError):
        bootstrap_pair_mean_ci([])
