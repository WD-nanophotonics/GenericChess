"""Exact finite surrogate arithmetic; no context estimator or game sampler."""
from fractions import Fraction


def _rational(value):
    if type(value) is not int and not isinstance(value, Fraction):
        raise ValueError('exact rational required')
    return Fraction(value)


def finite_service(rewards, survival, *, horizon=2):
    """Return sum P^k g for the explicit finite owned-mode surrogate.

    Absent mode rows/columns are unsupported, not zero. This arithmetic cannot
    establish that mode-conditional context refresh describes a real game.
    """
    if type(horizon) is not int or not 0 <= horizon <= 2 or not rewards:
        raise ValueError('nonempty modes and qualified horizon0..2 required')
    modes = tuple(rewards)
    if survival.keys() != rewards.keys():
        raise ValueError('complete survival mode rows required')
    g = {m: _rational(rewards[m]) for m in modes}
    if any(v < 0 for v in g.values()):
        raise ValueError('nonnegative unit-removal reward required')
    p = {}
    for m, row in survival.items():
        if row.keys() != rewards.keys():
            raise ValueError('complete survival mode columns required')
        p[m] = {n: _rational(row[n]) for n in modes}
        if any(v < 0 for v in p[m].values()) or sum(p[m].values()) > 1:
            raise ValueError('substochastic survival row required')
    v = {m: Fraction(0) for m in modes}
    for _ in range(horizon):
        v = {m: g[m] + sum((p[m][n]*v[n] for n in modes), Fraction(0)) for m in modes}
    return v


def exchangeable_hand_drop(tag_mass, hand_count):
    """A hidden own tag among n fungible same-base tokens, uniform drop choice.

    Return (still-held tag mass, tag mass put on board). The random physical
    identity is an explicitly declared extension of the unlabeled hand API.
    """
    mass = _rational(tag_mass)
    if not 0 <= mass <= 1 or type(hand_count) is not int or hand_count < 1:
        raise ValueError('tag probability and positive pre-drop hand count required')
    dropped = mass / hand_count
    return mass-dropped, dropped
