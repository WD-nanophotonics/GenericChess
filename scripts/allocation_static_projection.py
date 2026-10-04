"""Finite signed allocation projection; no game sampler or fitted coefficients."""
from fractions import Fraction as F
from scripts.public_task_intervals import probability


def signed_interval(pair):
    if len(pair)!=2 or any(type(v) is not int and not isinstance(v,F) for v in pair):
        raise ValueError('exact signed interval required')
    lo,hi=map(F,pair)
    if lo>hi:
        raise ValueError('ordered signed interval required')
    return lo,hi


def counts(values):
    if not values or any(type(m) is not str or not m for m in values):
        raise ValueError('explicit nonempty mode dictionary required')
    if any(type(n) is not int or n<0 for n in values.values()):
        raise ValueError('nonnegative integer physical counts required')
    return values


def token_weighted_prototypes(frames):
    """frames=(weight, full mode counts, signed total allocation intervals).

    Exact declared law weights sum to1. Unknown allocations must be explicitly
    bounded, never omitted; absent modes cannot silently get coefficient0.
    Returned component boxes preserve signs but not cross-component correlation.
    Caller supplies/authenticates the underlying common coalition game/law.
    """
    if not frames or len(frames)>128:
        raise ValueError('one to128 supplied arithmetic frames required')
    modes=set(counts(frames[0][1]))
    mass=F(0);denominator={m:F(0) for m in modes}
    lower={m:F(0) for m in modes};upper={m:F(0) for m in modes}
    for weight,inventory,allocations in frames:
        q=probability(weight);mass+=q
        counts(inventory)
        if set(inventory)!=modes or set(allocations)!=modes:
            raise ValueError('same complete mode support required for every frame')
        for m,n in inventory.items():
            lo,hi=signed_interval(allocations[m])
            if lo < -n or hi > n:
                raise ValueError('mode total outside supplied physical allocation range')
            denominator[m]+=q*n;lower[m]+=q*lo;upper[m]+=q*hi
    if mass!=1:
        raise ValueError('declared context law must sum to1')
    if any(n==0 for n in denominator.values()):
        raise ValueError('unobserved mode has no justified prototype')
    return {m:(lower[m]/denominator[m],upper[m]/denominator[m]) for m in sorted(modes)}


def inventory_score_interval(inventory,prototypes):
    """Conservative component-box score; not a correlated sharp task bound."""
    counts(inventory)
    if set(inventory)!=set(prototypes):
        raise ValueError('complete requested inventory coefficient coverage required')
    lo=hi=F(0)
    for m,n in inventory.items():
        a,b=signed_interval(prototypes[m]);lo+=n*a;hi+=n*b
    return lo,hi
