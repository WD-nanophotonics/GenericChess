"""Finite public-information task arithmetic; no game sampler or price fit."""
from fractions import Fraction as F


def probability(value):
    if type(value) is not int and not isinstance(value, F) or not 0 <= value <= 1:
        raise ValueError('exact probability in[0,1] required')
    return F(value)


def interval(pair):
    if len(pair) != 2:
        raise ValueError('lower/upper pair required')
    lo, hi = map(probability, pair)
    if lo > hi:
        raise ValueError('ordered task interval required')
    return lo, hi


def integrate_public_action(world_weights, world_intervals):
    """One chosen PUBLIC action, expectation over a complete joint hidden law.

    Caller authenticates worlds/payoffs and public action availability. Missing
    worlds never disappear or renormalize; use explicit[0,1] for unknown payoff.
    """
    if not world_weights or world_weights.keys() != world_intervals.keys():
        raise ValueError('same nonempty full hidden-world support required')
    weights = {k: probability(q) for k, q in world_weights.items()}
    if sum(weights.values()) != 1:
        raise ValueError('hidden-world law must sum to1')
    bounds = {k: interval(p) for k, p in world_intervals.items()}
    return tuple(sum((weights[k]*bounds[k][i] for k in weights), F(0)) for i in (0, 1))


def public_choice_bound(observed_action_intervals, *, maximize, complete):
    """Value bounds, NOT a canonical complete-selector action choice.

    Incomplete legal action enumeration retains all missing choices[0,1]. Range
    dominance can prove value1/max or0/min without proving a canonical tie.
    """
    if type(maximize) is not bool or type(complete) is not bool:
        raise ValueError('explicit bool controller/completeness required')
    bounds = [interval(p) for p in observed_action_intervals.values()]
    if complete and not bounds:
        raise ValueError('complete ongoing action set must be nonempty')
    if not bounds:
        return F(0), F(1)
    choose = max if maximize else min
    lower, upper = choose(p[0] for p in bounds), choose(p[1] for p in bounds)
    if not complete:
        if maximize:
            upper = F(1)
        else:
            lower = F(0)
    return lower, upper


def completion_custody_probability(joint_world_weights):
    """Keys are(completed, alive) bools. Never multiply marginal probabilities."""
    if any(not isinstance(k, tuple) or len(k) != 2 or any(type(v) is not bool for v in k)
           for k in joint_world_weights):
        raise ValueError('joint bool event worlds required')
    return integrate_public_action(joint_world_weights,
                                   {k: (int(all(k)), int(all(k))) for k in joint_world_weights})[0]
