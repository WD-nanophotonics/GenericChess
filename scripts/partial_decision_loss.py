"""Exact interval certificates for frozen choices, without evaluator calibration."""
from fractions import Fraction as F


def _rational(value):
    if type(value) is not int and not isinstance(value, F):
        raise ValueError('exact rational required')
    return F(value)


def _choices(intervals, owner):
    if type(owner) is not int or owner not in (0, 1) or not intervals:
        raise ValueError('nonempty choices and owner0/1 required')
    result = {}
    for key, pair in intervals.items():
        if len(pair) != 2:
            raise ValueError('interval pair required')
        lo, hi = map(_rational, pair)
        if not -1 <= lo <= hi <= 1:
            raise ValueError('goal interval outside [-1,1]')
        result[key] = (lo, hi) if owner == 0 else (-hi, -lo)
    return result


def regret_bounds(intervals, selected, owner=0):
    choices = _choices(intervals, owner)
    if selected not in choices:
        raise ValueError('selected choice missing')
    others = [pair for key, pair in choices.items() if key != selected]
    if not others:
        return F(0), F(0)
    lo, hi = choices[selected]
    return (max(F(0), max(p[0] for p in others)-hi),
            max(F(0), max(p[1] for p in others)-lo))


def paired_margin(intervals, candidate, baseline, owner=0):
    choices = _choices(intervals, owner)
    if candidate not in choices or baseline not in choices:
        raise ValueError('both selected choices required')
    if candidate == baseline:
        return F(0), F(0)
    a, c = choices[candidate], choices[baseline]
    return a[0]-c[1], a[1]-c[0]


def classify_regret(intervals, selected, tolerance=0, owner=0):
    tolerance = _rational(tolerance)
    if not 0 <= tolerance <= 2:
        raise ValueError('tolerance outside [0,2]')
    lo, hi = regret_bounds(intervals, selected, owner)
    verdict = ('certified_pass' if hi <= tolerance else
               'certified_failure' if lo > tolerance else 'inconclusive')
    return {'regret': (lo, hi), 'verdict': verdict}


def certify_population(roots, weights, delta):
    """roots: (choice intervals, candidate ID, baseline ID, root owner)."""
    delta = _rational(delta)
    if not 0 < delta <= 2 or not roots or len(roots) != len(weights):
        raise ValueError('positive margin and equal nonempty inputs required')
    weights = list(map(_rational, weights))
    if any(w < 0 for w in weights) or sum(weights) != 1:
        raise ValueError('probability weights required')
    lo = hi = F(0)
    for root, weight in zip(roots, weights):
        a, b = paired_margin(*root)
        lo += weight*a
        hi += weight*b
    verdict = ('certified_improvement' if lo >= delta else
               'certified_failure' if hi < delta else 'inconclusive')
    return {'margin': (lo, hi), 'required_margin': delta, 'verdict': verdict}
