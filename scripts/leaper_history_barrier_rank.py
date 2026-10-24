"""Scoped finite-game history reduction for automatic DRAW repetitions.

This consumes an already complete, qualified position-local alternating graph.
It does not establish position sufficiency for an arbitrary RuleSet. A current
history with q-1 earlier occurrences turns future arrivals at those vertices
into DRAW sinks; the current root itself stays playable. Ordinary lower-count
future draw stops do not create a win, while strict winning ranks avoid all
future repetitions. A finite remaining clock cuts off ranks longer than H.
"""
from scripts.leaper_retrograde import attractor

def solve(edges,sides,terminals,root,counts,*,limit,remaining):
    """Return player-0 WDL/rank from an admitted complete graph and history.

    terminals maps vertex -> winner 0/1/None. Existing terminal precedence is
    assumed and terminals are never replaced by repetition/clock draws.
    """
    n=len(edges)
    if len(sides)!=n or not 0<=root<n or limit<2 or remaining<0:
        raise ValueError('invalid finite-history contract')
    if any(s not in(0,1)for s in sides)or any(i not in range(n)or w not in(None,0,1)for i,w in terminals.items()):
        raise ValueError('invalid side/terminal')
    if any((bool(ee)if i in terminals else not ee)or any(type(j)is not int or not 0<=j<n or sides[i]==sides[j]for j in ee)for i,ee in enumerate(edges)):
        raise ValueError('graph must be complete, terminal-sink and alternating')
    if any(not 0<=i<n or not 0<=k<limit for i,k in counts.items()):
        raise ValueError('invalid ongoing incoming repetition count')
    barriers={i for i,k in counts.items()if k==limit-1 and i!=root and i not in terminals}
    ts=dict(terminals);ts.update({i:None for i in barriers})
    modified=[[]if i in barriers else ee for i,ee in enumerate(edges)]
    relative={i:0 if w is None else 1 if w==sides[i]else-1 for i,w in ts.items()}
    values,ranks=attractor(modified,relative)
    raw=values[root]*(1 if sides[root]==0 else-1);rank=ranks.get(root)
    value=raw if root in terminals or raw==0 or rank<=remaining else 0
    return dict(value=value,physical_barrier_value=raw,rank=rank,
        blocked=sorted(barriers),root=root,remaining=remaining,
        root_count=counts.get(root,0)),(modified,ts,values,ranks)

