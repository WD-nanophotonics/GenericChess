"""Narrow geometry/slot contract; actual Core remains legality authority."""
from dataclasses import replace
from types import SimpleNamespace
from collections import Counter
import pytest
from scripts import leaper_design as L
from generic_chess.ai.alphabeta.ordering import MoveOrderer, _quiet_geometry_targets
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.core.pieces import Piece
from generic_chess.core.coordinates import square_to_index
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.session.session import GameSession


def fixture():
    rule=L.definition(1,2)
    board=[None]*16
    for i,owner,tid in [(0,0,'K'),(6,0,'A'),(4,0,'B'),(15,1,'K'),(14,1,'A'),(10,1,'B')]:
        board[i]=Piece(owner,tid,tid)
    rule=replace(rule,initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)))
    c=L.compile_rule(rule);s=GameSession(c)
    return c,s


@pytest.mark.parametrize('directional',[False,True])
def test_table_matches_core_geometric_attack_reference_with_current_type_binding(directional):
    rule=L.definition(1,2)
    if directional:
        rule=replace(rule,piece_types=(rule.piece_types[0],replace(rule.piece_types[1],movement_atoms=(LeapAtom((0,1)),)),rule.piece_types[2]))
    c=L.compile_rule(rule);s=GameSession(c);table=_quiet_geometry_targets(c)
    assert table is not None
    for owner in (0,1):
        actual=set()
        for i,piece in enumerate(s.state.position.board):
            if piece is not None and piece.owner==owner:
                actual.update(table.get((owner,piece.current_type_id,i),()))
        assert actual==semantic_engine_for(c).attacked_squares(s.state.position,owner)


def test_only_eligible_slots_permute_and_q_never_consumes_feature():
    c,s=fixture();actions=s.legal_actions();ev=SimpleNamespace(capture_order_value=lambda *_:10**12)
    stats=SearchStatistics();orderer=MoveOrderer(c,stats);on=SearchTuning(use_quiet_geometric_coverage=True,use_countermove=True)
    covered=semantic_engine_for(c).attacked_squares(s.state.position,1)
    quiet=[a for a in actions if s.state.position.board[square_to_index(a.to_square,c.board_shape)] is None]
    safe=[a for a in quiet if square_to_index(a.to_square,c.board_shape) not in covered]
    attacked=[a for a in quiet if square_to_index(a.to_square,c.board_shape) in covered]
    assert safe and attacked
    # Force a covered quiet ahead by history; the new feature must consume it.
    for _ in range(10):orderer.record_history(0,attacked[0],on)
    base=orderer.order(s.state,actions,ev,2,None,None,replace(on,use_quiet_geometric_coverage=False))
    result=orderer.order(s.state,actions,ev,2,None,None,on)
    assert Counter(result)==Counter(base) and result!=base and stats.quiet_geometry_reorders==1
    assert orderer.order(s.state,actions,ev,-1,None,None,on)==base
    # Protect TT/killer/counter even if scalar capture values have arbitrary scale.
    previous=actions[0];tt=quiet[0];killer=quiet[1];counter=quiet[2]
    orderer.record_killer(2,killer);orderer.record_countermove(previous,counter)
    duplicated=list(actions)+[quiet[-1]]
    base=orderer.order(s.state,duplicated,ev,2,tt,previous,replace(on,use_quiet_geometric_coverage=False))
    result=orderer.order(s.state,duplicated,ev,2,tt,previous,on)
    assert Counter(result)==Counter(base)
    for i,a in enumerate(base):
        if a in (tt,killer,counter) or s.state.position.board[square_to_index(a.to_square,c.board_shape)] is not None:
            assert result[i] is a
    assert result[0]==tt


def test_all_equal_coverage_preserves_original_order_and_identities():
    c,s=fixture();ev=SimpleNamespace(capture_order_value=lambda *_:0)
    orderer=MoveOrderer(c);orderer._geometry_targets={};orderer._geometry_ready=True
    actions=s.legal_actions();on=SearchTuning(use_quiet_geometric_coverage=True)
    base=orderer.order(s.state,actions,ev,2,None,None,replace(on,use_quiet_geometric_coverage=False))
    assert orderer.order(s.state,actions,ev,2,None,None,on)==base
    assert MoveOrderer().order(s.state,actions,ev,2,None,None,on)==base


def test_admitted_quiet_transition_keeps_enemy_geometry_but_not_claimed_legality():
    c,s=fixture();engine=semantic_engine_for(c)
    before=engine.attacked_squares(s.state.position,1);count=0
    for action in s.legal_actions():
        if s.state.position.board[square_to_index(action.to_square,c.board_shape)] is not None:
            continue
        child=GameSession.replay(c,s.to_record());child.submit(action)
        assert engine.attacked_squares(child.state.position,1)==before
        count+=1
    assert count>=2


def test_cancelled_candidate_preserves_root_history_and_fallback_contract():
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    c,s=fixture();before=s.to_record()
    for enabled in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False,
                         tuning=SearchTuning(use_quiet_geometric_coverage=enabled))
        d=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=5000,max_time_seconds=1),
                          cancel_token=SimpleNamespace(is_cancelled=lambda:True))
        assert d.termination_reason=='cancelled'
        assert d.completed_depth==0 and d.runtime_depth_balanced
        assert s.to_record()==before


def test_large_board_declines_without_geometry_scan():
    from generic_chess.core.coordinates import BoardShape
    assert _quiet_geometry_targets(SimpleNamespace(board_shape=BoardShape(9,9))) is None


@pytest.mark.parametrize('when',['during_build','after_build'])
def test_new_preprocessing_cancellation_stays_in_search_fallback_boundary(monkeypatch,when):
    import generic_chess.ai.alphabeta.ordering as ordering
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.limits import SearchLimits
    c,s=fixture();before=s.to_record();control={'cancelled':False,'entered':False}
    original=ordering._quiet_geometry_targets
    def build(compiled,checkpoint=None):
        control['entered']=True
        calls=0
        def bounded():
            nonlocal calls
            calls+=1
            if when=='during_build' and calls==8:control['cancelled']=True
            checkpoint()
        value=original(compiled,bounded)
        if when=='after_build':control['cancelled']=True
        return value
    monkeypatch.setattr(ordering,'_quiet_geometry_targets',build)
    p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=False,
                     tuning=SearchTuning(use_quiet_geometric_coverage=True))
    d=p.choose_action(s,SearchLimits(max_depth=3,max_nodes=50000,max_time_seconds=3),
                     cancel_token=SimpleNamespace(is_cancelled=lambda:control['cancelled']))
    assert control['entered'] and d.termination_reason=='cancelled'
    assert d.completed_depth==0 and d.action in s.legal_actions()
    assert d.runtime_depth_balanced and s.to_record()==before


def test_off_and_q_do_not_build_geometry(monkeypatch):
    import generic_chess.ai.alphabeta.ordering as ordering
    c,s=fixture();ev=SimpleNamespace(capture_order_value=lambda *_:0)
    def forbidden(*_):raise AssertionError('geometry must not be consumed')
    monkeypatch.setattr(ordering,'_quiet_geometry_targets',forbidden)
    o=MoveOrderer(c)
    o.order(s.state,s.legal_actions(),ev,2,None,None,SearchTuning())
    o.order(s.state,s.legal_actions(),ev,-1,None,None,SearchTuning(use_quiet_geometric_coverage=True))


@pytest.mark.parametrize('kind',['ray','drop','effect','promotion','state_guard'])
def test_unsupported_semantics_fall_back_exactly(kind):
    rule=L.definition(1,2)
    if kind=='ray':
        rule=replace(rule,piece_types=rule.piece_types[:2]+(replace(rule.piece_types[2],movement_atoms=(RayAtom((1,0)),)),))
    if kind=='drop':rule=replace(rule,drop_allowed={**rule.drop_allowed,'A':((True,)*16,)*2})
    c=L.compile_rule(rule)
    if kind in ('effect','promotion','state_guard'):
        p=c.ir.patterns[0]
        changes={'effect':{'effects':p.effects+p.effects},'promotion':{'explicit_promotion_type':'A'},'state_guard':{'guards':(object(),)}}[kind]
        ir=replace(c.ir,patterns=(replace(p,**changes),)+c.ir.patterns[1:])
        c=SimpleNamespace(**{name:getattr(c,name) for name in ('board_size','board_shape','pass_enabled','no_progress_draw','piece_types','promotion_allowed','promotion_forced')},ir=ir)
    assert _quiet_geometry_targets(c) is None
