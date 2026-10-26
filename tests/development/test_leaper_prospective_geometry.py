"""Independent contracts for the prospective geometry-only research reader."""
from dataclasses import replace
from itertools import combinations

import pytest

from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, atom_targets
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.schema import RuleSet, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from scripts.leaper_prospective_geometry import (
    D4, checked, effective, vector, square, edges, joint_key, descriptor,
)

H = ((-1,0),(1,0))
V = ((0,-1),(0,1))
K = tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0))


def rule(b=H, horizon=128, matrix=D4[0]):
    n=4
    types = tuple(PieceType(name,name,tuple(LeapAtom(vector(v,matrix)) for v in offsets),
                            is_anchor=name=="K")
                  for name,offsets in (("K",K),("A",H),("B",b)))
    board=[None]*16
    for index,owner,name in ((0,0,"K"),(1,0,"A"),(8,0,"B"),(15,1,"K")):
        board[square(index,n,matrix)] = Piece(owner,name,name)
    return RuleSet(board_size=4,piece_types=types,
        initial_position=tuple(tuple(board[y*4:y*4+4]) for y in range(4)),
        capture_disposition="remove_from_game",
        drop_allowed={name:((False,)*16,)*2 for name in ("A","B")},
        max_ply=horizon,repetition_limit=4)


@pytest.mark.parametrize("bad",[(0,0),(True,1),(1.5,0)])
def test_not_a_zero_or_noninteger_leap(bad):
    with pytest.raises(ValueError): checked(4,[bad])


def test_effective_edges_independently_agree_with_core_atoms_for_both_owners():
    for n in (4,5,6):
        for dx in range(-5,6):
            for dy in range(-5,6):
                if (dx,dy)==(0,0): continue
                for owner in (0,1):
                    expected=set()
                    for source in range(n*n):
                        for target in atom_targets(n,owner,Square(source%n,source//n),LeapAtom((dx,dy))):
                            expected.add((source,target.file+n*target.rank))
                    assert set(edges(n,((dx,dy),),owner))==expected


@pytest.mark.parametrize("n",[4,5,6])
def test_each_displacement_has_analytically_known_number_of_edges(n):
    for dx in range(-5,6):
        for dy in range(-5,6):
            if (dx,dy)!=(0,0):
                assert len(edges(n,((dx,dy),)))==max(n-abs(dx),0)*max(n-abs(dy),0)


def test_dead_direction_alias_is_board_specific_and_not_rule_identity():
    assert edges(4,((1,0),(4,0)))==edges(4,((1,0),))
    assert joint_key(4,{"A":((1,0),(4,0))})==joint_key(4,{"A":((1,0),)})
    assert joint_key(5,{"A":((1,0),(4,0))})!=joint_key(5,{"A":((1,0),)})


def test_one_common_transform_required_for_multiple_types():
    assert joint_key(4,{"A":H})==joint_key(4,{"A":V})
    assert joint_key(4,{"A":H,"B":H})!=joint_key(4,{"A":H,"B":V})
    a=GameSession(compile_legacy_ruleset_for_semantic_execution(rule(H)))
    b=GameSession(compile_legacy_ruleset_for_semantic_execution(rule(V)))
    assert compute_fingerprint(rule(H))!=compute_fingerprint(rule(V))
    proj=lambda s:{(x.from_square.file,x.from_square.rank,x.to_square.file,x.to_square.rank) for x in s.legal_actions()}
    assert proj(a)!=proj(b)


def test_same_geometry_does_not_carry_the_clock_terminal_contract():
    short=rule(H,1);long=rule(H,128)
    assert joint_key(4,{"K":K,"A":H,"B":H})==joint_key(4,{"K":K,"A":H,"B":H})
    assert compute_fingerprint(short)!=compute_fingerprint(long)
    a=GameSession(compile_legacy_ruleset_for_semantic_execution(short))
    b=GameSession(compile_legacy_ruleset_for_semantic_execution(long))
    action=a.legal_actions()[0]
    a.submit(action);b.submit(action)
    assert a.state.terminal_status.is_terminal
    assert not b.state.terminal_status.is_terminal


@pytest.mark.parametrize("matrix",D4)
def test_joint_common_mapping_matches_literal_core_frontier(matrix):
    n=4
    original=GameSession(compile_legacy_ruleset_for_semantic_execution(rule(V)))
    mapped=GameSession(compile_legacy_ruleset_for_semantic_execution(rule(V,matrix=matrix)))
    expected={(square(a.from_square.file+n*a.from_square.rank,n,matrix),
               square(a.to_square.file+n*a.to_square.rank,n,matrix))
              for a in original.legal_actions()}
    actual={(a.from_square.file+n*a.from_square.rank,a.to_square.file+n*a.to_square.rank)
              for a in mapped.legal_actions()}
    assert actual==expected
    assert joint_key(n,{"K":K,"A":H,"B":V})==joint_key(
        n,{"K":tuple(vector(v,matrix) for v in K),
           "A":tuple(vector(v,matrix) for v in H),
           "B":tuple(vector(v,matrix) for v in V)})


def test_descriptors_are_not_an_equivalence_certificate():
    seen={}
    directions=[(x,y) for x in range(-3,4) for y in range(-3,4) if (x,y)!=(0,0)]
    witness=None
    for offsets in combinations(directions,2):
        d=descriptor(4,offsets);k=joint_key(4,{"T":offsets})
        if d in seen and seen[d]!=k:
            witness=(seen[d],k);break
        seen[d]=k
    assert witness is not None  # Independent finite counterexample search, no game solve.


@pytest.mark.parametrize("offsets,answer",[(((1,0),),True),(((1,0),(2,0)),False),(((2,0),),True)])
def test_underlying_bipartiteness_has_known_path_and_triangle_controls(offsets,answer):
    # A single forward edge has an undirected path, whereas +1,+2 gives triangles.
    assert descriptor(4,offsets)[-1] is answer


def test_directed_leftward_components_do_not_overlap():
    d=descriptor(4,((-1,0),))
    assert d[2]==(4,4,4,4)
    assert d[3]==(1,)*16
    assert sum(d[2])==sum(d[3])==16


def test_recorder_uses_actual_core_child_contract_not_frozen_catalog_refill():
    from generic_chess.core.transition import legal_successors
    from scripts.leaper_prospective_literal_catalog import child_observation
    compiled=compile_legacy_ruleset_for_semantic_execution(rule())
    state=GameSession(compiled).state
    action,child=next(iter(legal_successors(state,compiled)))
    row=child_observation(action,child)
    assert row["ply_count"]==1
    assert row["history_length"]==len(child.history)
    assert row["child"]["ply_count"]==child.ply_count
    assert not hasattr(child,"ply")


@pytest.mark.parametrize("n",[4,5,6])
def test_independent_burnside_orbit_count(n):
    from scripts.leaper_prospective_geometry_analysis import burnside
    assert burnside(n)=={4:172,5:447,6:970}[n]


def test_exact_two_direction_cycles_respect_finite_extent():
    from scripts.leaper_two_direction_components import analytic_scc,has_cycle
    assert not has_cycle(4,((2,0),(-3,0)))
    assert has_cycle(5,((2,0),(-3,0)))
    assert analytic_scc(4,((2,0),(-3,0)))==(1,)*16
    assert analytic_scc(5,((2,0),(-3,0)))==(5,)*5
    assert analytic_scc(5,((2,0),(-4,0)))==tuple(sorted([3]*5+[1]*10))


def test_unlabelled_geometry_union_does_not_preserve_quiet_capture_semantics():
    from scripts.leaper_geometry_relation_witness import definition as ir_rule
    from generic_chess.rules.compiler import compile_semantic_ruleset
    counts=[]
    for swap in (False,True):
        rr=ir_rule(swap)
        assert {tuple(a.geometry.offset) for a in rr.semantic_actions}=={(1,0),(0,1)}
        ss=GameSession(compile_semantic_ruleset(rr))
        counts.append(sum(a.from_square==Square(1,1) for a in ss.legal_actions()))
    assert counts==[2,0]


@pytest.mark.parametrize("n",[4,5])
def test_offboard_geometry_alias_does_not_preserve_generator_metadata(n):
    from generic_chess.generation.piece_generator import derive_is_promotable
    aa=(LeapAtom((1,1)),);bb=aa+(LeapAtom((0,-n)),)
    assert edges(n,[a.offset for a in aa])==edges(n,[a.offset for a in bb])
    assert derive_is_promotable(aa) is True
    assert derive_is_promotable(bb) is False
