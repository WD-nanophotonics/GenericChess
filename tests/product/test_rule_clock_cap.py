"""Exact hard-clock depth cap, caller limits and unsupported-policy boundaries."""
from dataclasses import replace
import pytest
from generic_chess.rules.schema import RuleSet,RuleAutomaticAdjudication
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.rule_clock import capped_pure_leaper_limits
from generic_chess.ai.limits import SearchLimits

def rule():
    k=PieceType('K','K',tuple(LeapAtom((x,y))for x in(-1,0,1)for y in(-1,0,1)if x or y),is_anchor=True)
    return RuleSet(board_size=3,piece_types=(k,),initial_position=((Piece(0,'K','K'),None,None),(None,None,None),(None,None,Piece(1,'K','K'))),capture_disposition='remove_from_game',max_ply=3,repetition_limit=4)

@pytest.mark.parametrize('compile',[compile_ruleset,compile_legacy_ruleset_for_semantic_execution])
def test_cap_stops_only_after_full_clock_and_retains_exact_prefix(compile):
    c=compile(rule());s=GameSession(c);before=s.state;limits=SearchLimits(max_depth=9,max_nodes=10000,quiescence_max_depth=0)
    off=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False)
    on=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False,cap_pure_leaper_rule_clock=True)
    a=[];b=[];d0=off.choose_action(s,limits,progress_callback=lambda *x:a.append(x));d1=on.choose_action(s,limits,progress_callback=lambda *x:b.append(x))
    assert d0.completed_depth==9 and d1.completed_depth==3 and d0.score==d1.score==0
    assert b==a[:3] and d1.nodes<d0.nodes and d1.action in s.legal_actions()
    assert limits.max_depth==9 and s.state==before and on.last_rule_clock_cap==3 and off.last_rule_clock_cap is None
    on.reset();assert on.last_rule_clock_cap is None


def test_cap_preserves_all_other_budget_fields_and_zero_depth_request():
    c=compile_ruleset(rule());s=GameSession(c);limits=SearchLimits(max_depth=9,max_nodes=7,max_time_seconds=.1,quiescence_max_depth=2,quiescence_hard_max_depth=5,quiescence_max_nodes=3)
    out=capped_pure_leaper_limits(s.state,c,limits);assert out==replace(limits,max_depth=3)
    assert capped_pure_leaper_limits(s.state,c,replace(limits,max_depth=None)).max_depth==3
    zero=replace(limits,max_depth=0);assert capped_pure_leaper_limits(s.state,c,zero)is zero
    shallow=replace(limits,max_depth=2);assert capped_pure_leaper_limits(s.state,c,shallow)is shallow


@pytest.mark.parametrize('compile',[compile_ruleset,compile_legacy_ruleset_for_semantic_execution])
def test_pending_automatic_policy_does_not_assume_max_ply_is_hard(compile):
    r=replace(rule(),automatic_adjudications=(RuleAutomaticAdjudication('threshold',2),));c=compile(r);s=GameSession(c);limits=SearchLimits(max_depth=9)
    assert capped_pure_leaper_limits(s.state,c,limits)is limits


def test_declared_rider_is_not_admitted_even_if_absent_on_current_board():
    r=rule();r=replace(r,piece_types=r.piece_types+(PieceType('R','R',(RayAtom((1,0)),)),),drop_allowed={'R':((False,)*9,)*2});c=compile_ruleset(r);s=GameSession(c);limits=SearchLimits(max_depth=9)
    assert capped_pure_leaper_limits(s.state,c,limits)is limits


def test_node_budget_still_aborts_before_complete_clock():
    c=compile_ruleset(rule());s=GameSession(c);p=AlphaBetaPlayer(c,use_disk_cache=False,cap_pure_leaper_rule_clock=True)
    d=p.choose_action(s,SearchLimits(max_depth=9,max_nodes=1,quiescence_max_depth=0))
    assert d.completed_depth<3 and d.termination_reason=='node_limit'and d.action in s.legal_actions()
    assert p.last_rule_clock_cap==3 # requested ceiling, never a completion claim
