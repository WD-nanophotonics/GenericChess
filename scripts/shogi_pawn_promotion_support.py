"""Full native-P support and partial distances under the existing virtual law."""
from collections import Counter
from fractions import Fraction as F
from scripts.shogi_direct_mode_bounds import TOTAL


def pawn_support_counts():
    prefix=Counter();promotion=Counter();zero=9*80*79
    for rank in range(8):
        k=max(1,6-rank)
        zero+=9*sum(80-j for j in range(1,k+1))
        for t in range(1,k+1):
            prefix[t]+=9*(80-t)
        promotion[k]+=9*(80-k)*(79-k)
    promotion_two=98*78
    remaining=dict(promotion);remaining[1]-=promotion_two
    return dict(zero=zero,reachable=TOTAL-zero,exact_prefix=dict(sorted(prefix.items())),
                quiet_promotion=dict(sorted(promotion.items())),promotion_two=promotion_two,
                exact_two=prefix[2]+promotion_two,remaining_promotion=remaining)


def pawn_support_interval(duration):
    if duration=='geometric_half':
        m=lambda t:F(1,2)**t
    elif duration=='linear_mixture':
        m=lambda t:F(2,(t+1)*(t+2))
    else:
        raise ValueError('use the existing two duration laws')
    c=pawn_support_counts()
    exact=sum(n*m(t) for t,n in c['exact_prefix'].items())+c['promotion_two']*m(2)
    lo=exact+sum(n*m(k+16) for k,n in c['remaining_promotion'].items())
    hi=exact+sum(n*m(max(3,k+1)) for k,n in c['remaining_promotion'].items())
    return lo/TOTAL,hi/TOTAL


def classify_pawn_world(source,target,blocker,owner):
    """Closed coordinate classification, not a compiled event executor."""
    if owner not in (0,1) or len({source,target,blocker})!=3 or any(not 0<=x<81 for x in (source,target,blocker)):
        raise ValueError('distinct9x9 world and owner0/1 required')
    if owner==1:
        source,target,blocker=80-source,80-target,80-blocker
    x,r=source%9,source//9
    if r==8:
        return ('zero',None)
    k=max(1,6-r)
    td=target//9-r if target%9==x else None
    bd=blocker//9-r if blocker%9==x else None
    if td is not None and 1<=td<=k and not (bd is not None and 1<=bd<td):
        return ('prefix',td)
    if bd is not None and 1<=bd<=k:
        return ('zero',None)
    q=(r+k)*9+x
    if k==1:
        dx,dy=target%9-q%9,target//9-q//9
        if (dx,dy) in ((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1)):
            return ('promotion_two',2)
    return ('promotion',k)
