"""Analytical full-mass controls; no game transitions or tour/goal search."""
from fractions import Fraction as F
from itertools import permutations
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.audit_static_semantic_material_prior_v2 import _promotion_targets,_promotion_forced


def test_knight_pairs_parity_partition_and_abstract_cycle_deletion():
    squares=[(x,y) for x in range(8) for y in range(8)]
    pairs=[(s,d) for s,d in permutations(squares,2)
           if sorted((abs(s[0]-d[0]),abs(s[1]-d[1])))==[1,2]]
    assert len(pairs)==8*7*6==336
    opposite=sum((sum(s)-sum(d))%2 for s,d in permutations(squares,2))
    assert opposite==2048
    assert (336*62,(opposite-336)*62,(4032-opposite)*62)==(20832,106144,123008)
    # Published Knight-cycle existence is separate. Check the general deletion
    # implication independently; don't pretend this ring is a Knight tour.
    for removed in range(64):
        path=[(removed+k)%64 for k in range(1,64)]
        assert len(set(path))==63 and removed not in path
        assert all((u-v)%64 in (1,63) for u,v in zip(path,path[1:]))
        assert len(path)-1==62


def test_pawn_zero_and_reachable_class_mass_without_overlap_loss():
    for n in (3,4,8):
        squares=[(x,y) for x in range(n) for y in range(n)]
        direct=[(s,d) for s,d in permutations(squares,2)
                if d[1]==s[1]+1 and abs(d[0]-s[0])==1]
        ahead=[(s,d) for s,d in permutations(squares,2) if d[0]==s[0] and d[1]>s[1]]
        last=[(s,d) for s,d in permutations(squares,2) if s[1]==n-1]
        assert len(direct)==2*(n-1)**2
        assert len(ahead)==n*n*(n-1)//2
        assert not set(last)&set(ahead) and not set(direct)&(set(last)|set(ahead))
    # Direct blockers can be anywhere else. The witness stratum needs d/b on
    # other files, leaving55 blocker squares, not all62.
    assert 98*62==6076 and 8*63*62+224*62==45136
    assert 56*56*55==172480 and 98*55==5390
    assert 172480-5390==167090
    assert 6076+45136+198772==249984


def test_full_interval_bounds_certify_parameter_reversals_without_selecting_gamma():
    def bounds(g):
        t=249984
        b=(F(33936,t)*g,(33936*g+88832*g*g)/t)
        n=((20832*g+106144*g**61+123008*g**62)/t,
           (20832*g+123008*g*g+106144*g**3)/t)
        p=((6076*g+167090*g**10)/t,(6076*g+198772*g*g)/t)
        r=(53760*g+194432*g*g+1792*g**3)/t
        return b,n,p,r
    for i in range(1,100):
        g=F(i,100);b,n,p,r=bounds(g)
        assert all(0<lo<=hi<1 for lo,hi in (b,n,p))
        assert r-n[1]==g*(1-g)*(32928+104352*g)/249984>0
        assert r-p[1]==g*(47684-4340*g+1792*g*g)/249984>0
    b,n,p,r=bounds(F(1,100));assert b[0]>n[1] and b[0]>p[1]
    b,n,p,r=bounds(F(99,100));assert n[0]>b[1] and p[0]>b[1]


def test_compiled_knight_and_pawn_masks_do_not_supply_hidden_movement():
    c=compile_semantic_ruleset(build_western_chess_ruleset())
    native=[p for p in c.ir.patterns if p.name in ('n_quiet','n_capture')]
    assert len(native)==2
    for p in native:
        assert not p.guards and not p.path and not p.slot_guards and p.promotion_mode=='none'
        assert all(c.ir.geometry[g].kind=='leap' for g in p.geometry_ids)
    for owner in (0,1):
        last=7 if owner==0 else 0;penultimate=6 if owner==0 else 1
        source=8*penultimate+3;target=8*last+3
        assert set(_promotion_targets(c,'P',owner,source,target))=={'Q','R','B','N'}
        assert _promotion_forced(c,'P',owner,target)
    for p in c.ir.patterns:
        if p.name in ('pawn_one_step','pawn_capture_left','pawn_capture_right'):
            assert p.promotion_mode=='inherit_compiled_masks' and not p.guards and not p.slot_guards
        if p.name.startswith('en_passant'):
            assert p.slot_guards
