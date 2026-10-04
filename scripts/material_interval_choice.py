"""Exact ongoing-child material box certificates, not goal/use validation.

The caller must supply a complete, authoritative ongoing-child feature table.
Terminal/claim qualification and a finite-service constructor stay separate.
No coefficient sampling, normalization by an uncertain maximum, or Core changes.
"""
from fractions import Fraction


def _bounds(intervals):
    if not intervals:
        raise ValueError('nonempty complete mode intervals required')
    for pair in intervals.values():
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError('lower/upper interval pair required')
        lo, hi = pair
        if any(type(x) is not int and not isinstance(x, Fraction) for x in pair):
            raise ValueError('exact rational interval required')
        if not 0 <= lo <= hi <= 2:
            raise ValueError('raw H2 interval must lie in[0,2]')


def _features(features, intervals):
    if any(key not in intervals for key in features):
        raise ValueError('missing encountered mode, including zero counts')
    if any(type(n) is not int for n in features.values()):
        raise ValueError('exact signed integer inventory counts required')


def material_margin_interval(first, second, intervals, *, owner):
    """Raw oriented pair margin; exact extrema over a closed coefficient box."""
    if type(owner) is not int or owner not in (0, 1):
        raise ValueError('owner0/1 required')
    _bounds(intervals)
    _features(first, intervals); _features(second, intervals)
    lo = hi = Fraction(0)
    for key in first.keys() | second.keys():
        difference = (first.get(key, 0)-second.get(key, 0))*(1 if owner == 0 else -1)
        lower, upper = intervals[key]
        lo += difference*(lower if difference >= 0 else upper)
        hi += difference*(upper if difference >= 0 else lower)
    return lo, hi


def certified_ongoing_material_choice(children, intervals, *, owner, complete=False):
    """Return a canonical choice only if EVERY box completion selects it.

    This certifies coefficient-insensitive choice, not a good goal decision.
    An incomplete table never falls back to a visited or midpoint best action.
    """
    if type(owner) is not int or owner not in (0, 1) or not children:
        raise ValueError('nonempty ongoing table and owner0/1 required')
    _bounds(intervals)
    for key, features in children.items():
        if not isinstance(key, str) or not key:
            raise ValueError('canonical string choice IDs required')
        _features(features, intervals)
    if complete is not True:
        return {'complete': False, 'selected': None, 'reason': 'incomplete choice table'}
    for first in sorted(children):
        margins = {}
        for second in sorted(children):
            if first == second:
                continue
            pair = material_margin_interval(children[first], children[second], intervals, owner=owner)
            margins[second] = pair
            # first wins equality only when its canonical ID sorts earlier.
            if pair[0] < 0 or (pair[0] == 0 and second < first):
                break
        else:
            return {'complete': True, 'selected': first, 'margins': margins,
                    'reason': 'same canonical selection throughout coefficient box'}
    return {'complete': True, 'selected': None,
            'reason': 'coefficient uncertainty can change canonical selection'}
