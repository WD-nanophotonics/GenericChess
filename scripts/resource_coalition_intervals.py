"""Exact allocation of supplied task intervals; no legal-game value oracle."""
from fractions import Fraction as F
from itertools import combinations
from math import comb
from scripts.public_task_intervals import interval


def _inputs(resources, supplied):
    if not resources or len(resources)>7 or any(type(r) is not str or not r for r in resources):
        raise ValueError('one to seven named physical resources required')
    universe=frozenset(resources)
    if len(universe)!=len(resources):
        raise ValueError('physical resource IDs must be distinct')
    if any(type(s) is not frozenset or not s<=universe for s in supplied):
        raise ValueError('coalition keys must be physical-resource frozensets')
    bounds={s:interval(p) for s,p in supplied.items()}
    for size in range(len(resources)+1):
        for group in combinations(resources,size):
            bounds.setdefault(frozenset(group),(F(0),F(1)))
    return universe,bounds


def allocation_intervals(resources, supplied):
    """Sharp component bounds over a RECTANGULAR supplied value uncertainty set.

    Every missing coalition remains[0,1]. Signed values are intentional: added
    physical resources are not proven monotone legal-game interventions. Shared
    coalition variables are collected before interval evaluation. These boxes
    are not a joint law or simultaneous independent allocations.
    """
    universe,bounds=_inputs(resources,supplied);n=len(resources);result={}
    for actor in resources:
        coefficients={}
        for s in bounds:
            if actor in s:
                coefficient=F(1,n*comb(n-1,len(s)-1))
            else:
                coefficient=-F(1,n*comb(n-1,len(s)))
            coefficients[s]=coefficient
        lo=hi=F(0)
        for s,c in coefficients.items():
            a,b=bounds[s]
            lo+=c*(a if c>0 else b)
            hi+=c*(b if c>0 else a)
        result[actor]=(lo,hi)
    return result


def allocation_total_interval(resources,supplied):
    """Use exact shared-variable efficiency, not sum of component boxes."""
    universe,bounds=_inputs(resources,supplied)
    a,b=bounds[universe];c,d=bounds[frozenset()]
    return a-d,b-c


def context_marginal_interval(resources,supplied,actor,background):
    universe,bounds=_inputs(resources,supplied)
    if actor not in universe or type(background) is not frozenset or not background<=universe or actor in background:
        raise ValueError('known actor absent from a valid background required')
    a,b=bounds[background|{actor}];c,d=bounds[background]
    return a-d,b-c


def pair_interaction_interval(resources,supplied,a,b,background=frozenset()):
    """Mixed difference with the SAME event/background, not new task labels."""
    universe,bounds=_inputs(resources,supplied)
    if (a==b or a not in universe or b not in universe or type(background) is not frozenset
            or not background<=universe or background&{a,b}):
        raise ValueError('distinct actors absent from a valid common background required')
    coefficients={background:F(1),background|{a}:-F(1),background|{b}:-F(1),background|{a,b}:F(1)}
    lower=upper=F(0)
    for s,c in coefficients.items():
        lo,hi=bounds[s]
        lower+=c*(lo if c>0 else hi);upper+=c*(hi if c>0 else lo)
    return lower,upper
