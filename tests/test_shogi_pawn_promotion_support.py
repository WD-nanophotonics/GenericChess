"""Independent forced-prefix simulation and algebraic support controls."""
from collections import Counter
from fractions import Fraction as F
from itertools import permutations
from scripts.shogi_pawn_promotion_support import pawn_support_counts,pawn_support_interval,classify_pawn_world
from scripts.shogi_direct_mode_bounds import TOTAL,partial_raw_interval
from scripts.gold_contact_routing import gold_route


def simulate_prefix(s,d,b,owner):
    # Walk unique native Pawn squares; no classification formula or graph search.
    sign=1 if owner==0 else -1
    zone={6,7,8} if owner==0 else {0,1,2}
    square=s
    for depth in range(1,9):
        rank=square//9+sign
        if not 0<=rank<9 or rank*9+square%9==b:
            return ('zero',None,None)
        nxt=rank*9+square%9
        if nxt==d:
            return ('prefix',depth,None)
        if square//9 in zone or rank in zone:
            return ('promotion',depth,nxt)
        square=nxt
    raise AssertionError('unique prefix must stop or promote')


def test_complete_world_partition_by_independent_prefix_walk():
    c=pawn_support_counts()
    for owner in (0,1):
        masses=Counter();prefix=Counter();promo=Counter()
        for s,d,b in permutations(range(81),3):
            kind,cost,q=simulate_prefix(s,d,b,owner)
            actual,depth=classify_pawn_world(s,d,b,owner)
            if kind=='zero':
                assert actual=='zero';masses['zero']+=1
            elif kind=='prefix':
                assert (actual,depth)==('prefix',cost);prefix[cost]+=1
            else:
                promo[cost]+=1
                if actual=='promotion_two':masses['promotion_two']+=1
                else:assert (actual,depth)==('promotion',cost)
        assert masses['zero']==c['zero']==72918
        assert prefix==c['exact_prefix'] and promo==c['quiet_promotion']
        assert masses['promotion_two']==c['promotion_two']==7644
        assert masses['zero']+sum(prefix.values())+sum(promo.values())==TOTAL


def test_support_and_first_two_distances_are_not_silently_point_estimated():
    c=pawn_support_counts()
    assert c['exact_prefix']=={1:5688,2:3510,3:2772,4:2052,5:1350,6:666}
    assert c['reachable']==439002 and c['exact_two']==11154
    assert c['zero']-62568==10350
    for law in ('geometric_half','linear_mixture'):
        lo,hi=pawn_support_interval(law)
        oldlo,oldhi=partial_raw_interval('P',law)
        assert oldlo<lo<hi<oldhi


def test_native_prefix_and_promoted_route_witness_keeps_source_vacating():
    # Sourcea1, targetb1, blockerb7: P promotes a7; the clear Gold route returns via a1.
    s,d,b=0,1,55
    kind,k,q=simulate_prefix(s,d,b,0)
    assert (kind,k,q)==('promotion',6,54)
    route=gold_route(q,d,b)
    assert route[-1]==d and len(route)-1<=16
    assert 0 in route  # Original source is vacant, not a second permanent blocker.
    assert classify_pawn_world(0,1,45,0)==('zero',None)  # Blocker before zone.
    assert classify_pawn_world(0,36,45,0)==('prefix',4)  # Earlier designated removal.


def test_merged_support_uses_correct_residual_moments():
    c=pawn_support_counts();m=lambda t:F(2,(t+1)*(t+2))
    exact=sum(n*m(t) for t,n in c['exact_prefix'].items())+7644*m(2)
    lo,hi=pawn_support_interval('linear_mixture')
    assert lo*TOTAL==exact+sum(n*m(k+16) for k,n in c['remaining_promotion'].items())
    assert hi*TOTAL==exact+sum(n*m(max(3,k+1)) for k,n in c['remaining_promotion'].items())
