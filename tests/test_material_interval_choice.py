from fractions import Fraction as F
from itertools import product

import pytest

from scripts.material_interval_choice import (
    material_margin_interval, certified_ongoing_material_choice,
)


def test_pair_extrema_match_independent_corner_scores_for_both_owners():
    boxes = ((0, 0), (0, 1), (F(1, 2), 2), (1, 2))
    for x, y, da, db, owner in product(boxes, boxes, range(-2, 3), range(-2, 3), (0, 1)):
        first, second = {'A': da, 'B': 0}, {'A': 0, 'B': -db}
        # Direct scores at independent closed-box vertices, not a sign formula.
        scores = [(da*a+db*b)*(1 if owner == 0 else -1)
                  for a, b in product(x, y)]
        assert material_margin_interval(first, second, {'A': x, 'B': y}, owner=owner) == (min(scores), max(scores))


def test_complete_choice_certificate_matches_all_corner_argmax_selections():
    boxes = ((0, 0), (0, 1), (F(1, 2), 2))
    feature_options = ({'A': 1, 'B': 0}, {'A': 0, 'B': 1},
                       {'A': -1, 'B': 1}, {'A': 1, 'B': 1})
    for x, y, features, owner in product(boxes, boxes, product(feature_options, repeat=3), (0, 1)):
        children = dict(zip(('a', 'b', 'z'), features))
        chosen = set()
        for a, b in product(x, y):
            scores = {key: value['A']*a+value['B']*b for key, value in children.items()}
            best = (max if owner == 0 else min)(scores.values())
            chosen.add(min(key for key, score in scores.items() if score == best))
        result = certified_ongoing_material_choice(children, {'A': x, 'B': y}, owner=owner, complete=True)
        assert result['selected'] == (next(iter(chosen)) if len(chosen) == 1 else None)


def test_irrelevant_mode_precision_and_tie_boundary_do_not_force_sampling():
    children = {'a': {'A': 1, 'B': 3}, 'z': {'A': 0, 'B': 3}}
    box = {'A': (0, 1), 'B': (0, 2)}
    # Arbitrarily uncertain B cancels. A can be0, but a wins the equality tie.
    assert certified_ongoing_material_choice(children, box, owner=0, complete=True)['selected'] == 'a'
    swapped = {'z': children['a'], 'a': children['z']}
    assert certified_ongoing_material_choice(swapped, box, owner=0, complete=True)['selected'] is None
    assert certified_ongoing_material_choice(children, box, owner=0)['selected'] is None


def test_invalid_or_missing_intervals_never_become_zero_or_midpoint_fallback():
    for box in ({'A': (0, .5)}, {'A': (2, 1)}, {'A': (-1, 1)}, {'A': (0, 3)}):
        with pytest.raises(ValueError):
            material_margin_interval({'A': 1}, {}, box, owner=0)
    with pytest.raises(ValueError, match='missing encountered'):
        material_margin_interval({'A': 0}, {}, {'B': (0, 2)}, owner=0)
    with pytest.raises(ValueError, match='owner'):
        material_margin_interval({'A': 1}, {}, {'A': (0, 2)}, owner=True)
    with pytest.raises(ValueError, match='integer'):
        material_margin_interval({'A': F(1, 2)}, {}, {'A': (0, 2)}, owner=0)
