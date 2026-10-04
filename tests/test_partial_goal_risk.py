from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path

import pytest

from scripts.audit_partial_goal_risk import audit, certify, quadratic_bounds


def test_frozen_partial_control_certificate():
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/partial_goal_risk_20261004.json').read_text())
    assert audit() == recorded
    result = audit()['partial_control']
    assert result['candidate_risk'] == ['3/16', '7/16']
    assert result['baseline_risk'] == ['3/4', '1']
    assert result['margin'] == ['37/80', '39/80']
    assert result['verdict'] == 'certified_improvement'


def test_unknown_not_zero_and_wrong_sign_rejected():
    assert certify([(-1, 1)], [0], [0], [1])['verdict'] == 'inconclusive'
    assert certify([(1, 1)], [-1], [0], [1])['verdict'] == 'certified_failure'
    assert certify([(0, 0)], [0], [0], [1])['verdict'] == 'inconclusive'


def test_extrema_include_interior_and_contain_rational_grid():
    assert quadratic_bounds(F(1), F(-1), F(0), F(0), F(1)) == (F(-1, 4), F(0))
    assert quadratic_bounds(F(-1), F(1), F(0), F(0), F(1)) == (F(0), F(1, 4))
    for a, b, c in product((F(-1), F(0), F(1)), repeat=3):
        low, high = quadratic_bounds(a, b, c, F(-1), F(1))
        for i in range(-20, 21):
            x = F(i, 20)
            assert low <= a*x*x+b*x+c <= high


def test_all_partial_completions_obey_paired_gate():
    for u, v in product((F(-1), F(-1, 2), F(0), F(1, 2), F(1)), repeat=2):
        resolved = certify([(1, 1), (-1, -1), (u, u), (v, v)],
                           [F(1, 2), F(-1, 2), 0, 0], [0]*4,
                           [F(3, 8), F(3, 8), F(1, 8), F(1, 8)])
        assert resolved['verdict'] == 'certified_improvement'
        assert F(37, 80) <= resolved['margin'][0] <= F(39, 80)


def test_invalid_measure_intervals_and_length_fail_closed():
    for args in (([], [], [], []), ([(-1, 1)], [], [0], [1]),
                 ([(1, -1)], [0], [0], [1]), ([(-2, 1)], [0], [0], [1]),
                 ([(-1, 1)], [0], [0], [F(1, 2)]),
                 ([(-1, 1)], [0.5], [0], [1])):
        with pytest.raises(ValueError):
            certify(*args)
