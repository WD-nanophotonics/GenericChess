"""Analytic partial board-mode envelopes under the declared uniform virtual law."""
from fractions import Fraction as F

TOTAL = 81*80*79
GOLD = ((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))
LEAPS = {
    'P':((0,1),), 'N':((-1,2),(1,2)),
    'S':((0,1),(-1,1),(1,1),(-1,-1),(1,-1)),
    **{t:GOLD for t in ('G','TP','TL','TN','TS')},
    'TB':((0,1),(0,-1),(-1,0),(1,0)),
    'TR':((-1,-1),(-1,1),(1,-1),(1,1)),
    'L':(),
}
RAYS = {'L':((0,1),), 'TB':((-1,-1),(-1,1),(1,-1),(1,1)),
        'TR':((0,1),(0,-1),(-1,0),(1,0))}


def direct_and_zero(tid):
    """Zero is a proved motionless subset, never all unreachable worlds."""
    if tid not in LEAPS:
        raise ValueError('ordinary qualified current Shogi board mode required')
    direct = sum((9-abs(x))*(9-abs(y))*79 for x,y in LEAPS[tid])
    direct += {'L':24840, 'TB':63120, 'TR':99360}.get(tid,0)
    zero = {'P':62568, 'L':62568, 'N':114866, 'S':158}.get(tid,0)
    return direct, zero


def partial_raw_interval(tid, duration):
    if duration=='geometric_half':
        m=lambda t:F(1,2)**t
    elif duration=='linear_mixture':
        m=lambda t:F(2,(t+1)*(t+2))
    else:
        raise ValueError('only the two declared duration laws')
    direct,zero=direct_and_zero(tid)
    lo=F(direct,TOTAL)*m(1)
    return lo,lo+F(TOTAL-direct-zero,TOTAL)*m(2)
