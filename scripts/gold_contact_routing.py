"""Constructive orthogonal Gold route with one blocker; no graph search."""
from fractions import Fraction as F
from scripts.gold_two_frontier import gold_two_counts
from scripts.shogi_direct_mode_bounds import TOTAL


def _line(a,b,n):
    x,y=a%n,a//n;u,v=b%n,b//n
    if x!=u and y!=v:
        raise ValueError('orthogonal segment required')
    dx=0 if x==u else 1 if u>x else -1
    dy=0 if y==v else 1 if v>y else -1
    out=[a]
    while (x,y)!=(u,v):
        x+=dx;y+=dy;out.append(y*n+x)
    return out


def gold_route(source,target,blocker,n=9):
    if n<2 or len({source,target,blocker})!=3 or any(type(x) is not int or not 0<=x<n*n for x in (source,target,blocker)):
        raise ValueError('distinct in-board source/target/blocker, n>=2 required')
    x,y=source%n,source//n;u,v=target%n,target//n
    if x!=u and y!=v:
        for corner in (y*n+u,v*n+x):
            path=_line(source,corner,n)+_line(corner,target,n)[1:]
            if blocker not in path:
                return path
        raise AssertionError('two L routes have disjoint interiors')
    path=_line(source,target,n)
    if blocker not in path:
        return path
    if x==u:
        offset=1 if x<n-1 else -1
        a=source+offset;b=target+offset
    else:
        offset=n if y<n-1 else -n
        a=source+offset;b=target+offset
    return [source]+_line(a,b,n)+[target]


def gold_reachability_lower(duration):
    m=(lambda t:F(1,2)**t) if duration=='geometric_half' else (
        (lambda t:F(2,(t+1)*(t+2))) if duration=='linear_mixture' else None)
    if m is None:
        raise ValueError('two declared duration laws required')
    c=gold_two_counts()
    return (c['direct']*m(1)+c['second']*m(2)+c['remaining']*m(16))/TOTAL
