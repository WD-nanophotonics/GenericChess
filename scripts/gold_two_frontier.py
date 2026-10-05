"""Gold2 intersection census only; no complete contact graph or game labels."""
from collections import Counter
from fractions import Fraction as F
from scripts.shogi_direct_mode_bounds import GOLD,TOTAL


def destinations(source):
    x,y=source%9,source//9
    return {9*(y+dy)+x+dx for dx,dy in GOLD if 0<=x+dx<9 and 0<=y+dy<9}


def gold_two_counts():
    multiplicities=Counter();direct_pairs=0
    for s in range(81):
        first=destinations(s)
        for d in range(81):
            if d==s:
                continue
            if d in first:
                direct_pairs+=1
                continue
            if abs(s%9-d%9)>2 or abs(s//9-d//9)>2:
                multiplicities[0]+=1
                continue
            common={u for u in first if d in destinations(u)}
            multiplicities[len(common)]+=1
    direct=direct_pairs*79
    second=sum(pairs*(78 if n==1 else 79) for n,pairs in multiplicities.items() if n)
    return dict(direct=direct,second=second,remaining=TOTAL-direct-second,
                direct_pairs=direct_pairs,nondirect_pair_multiplicity=dict(sorted(multiplicities.items())))


def gold_partial_interval(duration):
    m=(lambda t:F(1,2)**t) if duration=='geometric_half' else (
        (lambda t:F(2,(t+1)*(t+2))) if duration=='linear_mixture' else None)
    if m is None:
        raise ValueError('use the two existing duration laws')
    counts=gold_two_counts()
    lo=(counts['direct']*m(1)+counts['second']*m(2))/TOTAL
    return lo,lo+counts['remaining']*m(3)/TOTAL
