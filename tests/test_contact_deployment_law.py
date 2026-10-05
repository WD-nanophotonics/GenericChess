"""Finite law controls, no game/events or coefficient observations."""
from fractions import Fraction as F
from itertools import permutations


def laws(n,mask):
    a={};b={}
    for d,t in permutations(range(n),2):
        available=mask-{d,t}
        if not available:
            raise ValueError('no legal drop in this world; failure law required')
        for q in available:
            a[q,d,t]=F(1,n*(n-1)*len(available))
    for q in mask:
        for d,t in permutations(set(range(n))-{q},2):
            b[q,d,t]=F(1,len(mask)*(n-1)*(n-2))
    return a,b


def test_unrestricted_random_deployment_has_board_triple_marginal():
    for n in (3,4,5):
        a,b=laws(n,set(range(n)))
        assert a==b and sum(a.values())==1
        assert set(a.values())=={F(1,n*(n-1)*(n-2))}
        # Arbitrary fixed physical task values, including failures; no conditioning.
        g=F(2,3)
        f={triple:0 if sum(triple)%3==0 else g**(1+triple[0]%2) for triple in a}
        board=sum(a[t]*f[t] for t in a)
        held=sum(a[t]*g*f[t] for t in a)
        assert held==g*board


def test_restricted_mask_joint_laws_and_total_variation():
    for n,m in ((5,3),(6,3),(6,4),(6,5)):
        mask=set(range(m));a,b=laws(n,mask)
        assert a.keys()==b.keys() and sum(a.values())==sum(b.values())==1
        for (q,d,t),p in a.items():
            k=int(d in mask)+int(t in mask)
            assert p/b[q,d,t]==F(m*(n-2),n*(m-k))
        tv=sum(abs(a[t]-b[t]) for t in a)/2
        assert tv==F(2*(m-1)*(n-m),n*(n-1)*(n-2))
        # The sign-indicator payoff attains TV and exhibits demand-law bias.
        assert sum(a[t]-b[t] for t in a if a[t]>b[t])==tv
        pair=(0,1)
        assert sum(p for (_,d,t),p in a.items() if (d,t)==pair)==F(1,n*(n-1))
        assert sum(p for (_,d,t),p in b.items() if (d,t)==pair)!=F(1,n*(n-1))


def test_hiding_fixed_target_leaves_no_always_legal_drop():
    n=5;blocker=0
    worlds=set(range(n))-{blocker}
    common=set(range(n))
    for target in worlds:
        common &= set(range(n))-{target,blocker}
    assert common==set()
    import pytest
    with pytest.raises(ValueError,match='failure law required'):
        laws(5,{0,1})


def test_mask_law_error_is_bounded_without_mode_or_guard_equivalence():
    n=6;m=4;a,b=laws(n,set(range(m)));g=F(3,5)
    tv=F(2*(m-1)*(n-m),n*(n-1)*(n-2))
    for divisor in (2,3,4):
        f={t:0 if sum(t)%divisor==0 else g**(1+t[0]%3) for t in a}
        gap=abs(sum((a[t]-b[t])*g*f[t] for t in a))
        assert gap<=g**2*tv
    assert F(2*71*9,81*80*79)==F(71,28440)
    assert F(2*62*18,81*80*79)==F(31,7110)
