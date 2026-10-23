"""Finite complete-frontier checks of the quantity-dependent path polynomial."""
from dataclasses import replace
import itertools
import pytest
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import (template,multi_actor_forward2_polynomial,
    forward2_orbit_polynomial,evaluate_orbit_polynomial)


def test_single_actor_retains_exact_existing_coefficient_law():
    for n,spec in [(4,(0,2,13)),(5,(0,11,24)),(6,(0,13,35))]:
        assert multi_actor_forward2_polynomial(spec[0],(spec[1],),spec[2],n)==forward2_orbit_polynomial(spec,n)


def test_two_actor_core_boundary_has_nonnegative_cubic_terms():
    p=multi_actor_forward2_polynomial(0,(11,7),24,5)
    assert p==multi_actor_forward2_polynomial(0,(7,11),24,5)
    assert p['0,1,3']==4
    assert all(v>=0 for t,v in p.items() if len(t.split(','))==3)
    assert max(len(t.split(',')) if t else 0 for t in p)==3
    assert [evaluate_orbit_polynomial(p,m) for m in (4,5,6,7,12,13,14,15)]==[23,43,35,51,30,34,36,40]


def test_three_actor_fourth_difference_is_real_core_not_zero_mask():
    n=5;actors=(6,7,11);p=multi_actor_forward2_polynomial(0,actors,24,n)
    assert p['0,1,3,4']==-4
    board=[None]*25
    for sq,owner,tid in [(0,0,'K'),(24,1,'K')]+[(a,0,'A') for a in actors]:board[sq]=L.Piece(owner,tid,tid)
    difference=0
    for bits in itertools.product((0,1),repeat=4):
        mask=4|sum(x*(1<<j) for x,j in zip(bits,(0,1,3,4),strict=True))
        r=replace(template(mask,n,(0,6,24)),initial_position=tuple(tuple(board[5*y:5*y+5]) for y in range(5)))
        c=L.compile_rule(r);ss=L.GameSession(c)
        width=sum(0 if child.terminal_status.is_terminal else len(L.legal_successors(child,c)) for _,child in L.legal_successors(ss.state,c))
        assert width==evaluate_orbit_polynomial(p,mask)
        difference+=(-1)**(4-sum(bits))*width
    assert difference==-4


@pytest.mark.parametrize('k,aa,v,n',[(0,(0,),24,5),(0,(1,),6,5),(0,(),24,5),(0,(1,),24,2)])
def test_common_safe_plain_root_scope_is_required(k,aa,v,n):
    with pytest.raises(ValueError):multi_actor_forward2_polynomial(k,aa,v,n)


def test_static_minimum_respects_board_and_singleton_obstruction():
    from scripts.leaper_rule_coordinates import minimum_static_ordinary_count,static_quantity_witness
    positive={m for m in range(1,32) if any((m&p)==p for p in (3,5,10,12,24))}
    assert len(positive)==20
    for n in (3,4,5,6):
        for m in range(1,32):
            expected=1 if m in positive else None if n==3 and m==16 else 2
            assert minimum_static_ordinary_count(m,n)==expected
            w=static_quantity_witness(m,n)
            assert (w is None)==(expected is None)
            if w:assert len(w['ordinary'])==expected


def _static_compiled(mask,n):
    board=[[None]*n for _ in range(n)];board[0][0]=L.Piece(0,'K','K');board[-1][-1]=L.Piece(1,'K','K')
    return L.compile_rule(replace(template(mask,n,(0,1,n*n-1)),initial_position=tuple(map(tuple,board))))


def test_five_two_actor_constructions_are_real_static_mates():
    from scripts.leaper_rule_coordinates import static_quantity_witness
    from generic_chess.core.semantic_executor import semantic_engine_for
    for mask,n in ((1,3),(2,3),(4,3),(8,3),(16,4)):
        c=_static_compiled(mask,n);w=static_quantity_witness(mask,n);b=[None]*(n*n);flat=lambda p:p[0]+n*p[1]
        for p,owner,tid in [(w['king0'],0,'K'),(w['king1'],1,'K')]+[(a,0,'A') for a in w['ordinary']]:b[flat(p)]=L.Piece(owner,tid,tid)
        pos=replace(c.initial_position,board=tuple(b),side_to_move=1);e=semantic_engine_for(c)
        assert e.in_check(pos,1) and not e.legal_actions(pos)


def test_maximal_3x3_diagonal_two_inventory_still_has_safe_corner_escape():
    from generic_chess.core.semantic_executor import semantic_engine_for
    c=_static_compiled(16,3);b=[L.Piece(0,'A','A')]*9;b[2]=L.Piece(0,'K','K');b[0]=L.Piece(1,'K','K')
    pos=replace(c.initial_position,board=tuple(b),side_to_move=1);e=semantic_engine_for(c)
    assert e.in_check(pos,1)
    actions=e.legal_actions(pos)
    assert any(a.source==0 and a.target==3 for a in actions)
