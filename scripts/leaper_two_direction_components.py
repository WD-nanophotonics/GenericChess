"""Independent strong-component formula for at most two translation leaps.

This is a movement-graph theorem, never a legal game-state/WDL/TT theorem.
"""
from collections import Counter
from math import gcd

from scripts.leaper_prospective_geometry import checked


def analytic_scc(n, offsets):
    raw=checked(n,offsets)
    if len(raw)>2: raise ValueError("theorem covers at most two distinct directions")
    if len(raw)<2: return (1,)*(n*n)
    (x,y),(u,v)=raw
    if x*v-y*u != 0 or x*u+y*v >= 0:
        # A common strictly increasing linear potential exists.
        return (1,)*(n*n)
    a=gcd(abs(x),abs(y));b=gcd(abs(u),abs(v))
    px,py=x//a,y//a
    assert (u,v)==(-b*px,-b*py)
    g=gcd(a,b);q=(a+b)//g
    # Integer board points on each primitive parallel line form an interval.
    lines=Counter(px*j-py*i for i in range(n) for j in range(n))
    sizes=[]
    for length in lines.values():
        for residue in range(min(g,length)):
            count=(length-1-residue)//g+1
            if count>=q: sizes.append(count)
            else: sizes.extend([1]*count)
    assert sum(sizes)==n*n
    return tuple(sorted(sizes))


def has_cycle(n,offsets):
    raw=checked(n,offsets)
    if len(raw)!=2: return False
    (x,y),(u,v)=raw
    if x*v-y*u != 0 or x*u+y*v >= 0: return False
    a=gcd(abs(x),abs(y));b=gcd(abs(u),abs(v));g=gcd(a,b)
    return (a+b-g)*max(abs(x//a),abs(y//a)) <= n-1
