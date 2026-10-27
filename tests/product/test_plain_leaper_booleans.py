"""Exact Boolean projection, independently checked against generic Core."""
from dataclasses import replace
import random
import pytest
from scripts import leaper_design as L
from generic_chess.ai.alphabeta.leaper_boolean import PlainLeaperBooleans
from generic_chess.core.pieces import Piece
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.session.session import GameSession


def setup(masks=(1,2),directional=False):
    rule=L.definition(*masks)
    if directional:rule=replace(rule,piece_types=(rule.piece_types[0],replace(rule.piece_types[1],movement_atoms=(LeapAtom((0,1)),)),rule.piece_types[2]))
    c=L.compile_rule(rule);s=GameSession(c);p=PlainLeaperBooleans(c)
    return c,s,p


@pytest.mark.parametrize('masks',[(1,2),(3,8),(8,16),(17,31)])
@pytest.mark.parametrize('directional',[False,True])
def test_arbitrary_physical_boards_match_generic_core(masks,directional):
    c,s,p=setup(masks,directional);rng=random.Random(128773)
    assert p.admitted
    for _ in range(100):
        squares=rng.sample(range(16),6);board=[None]*16
        for i,(owner,tid) in zip(squares,[(0,'K'),(1,'K'),(0,'A'),(0,'B'),(1,'A'),(1,'B')]):board[i]=Piece(owner,tid,tid)
        position=replace(s.state.position,board=tuple(board),side_to_move=rng.randrange(2))
        before=position
        for side in (0,1):assert p.in_check(position,side)==p.engine.in_check(position,side)
        assert p.has_legal_action(position)==p.engine.has_legal_action(position)
        assert position==before
    assert p.metrics['fallbacks']==0 and p.metrics['cache_hits']>0


def test_legal_move_capture_and_undo_restore_all_core_predicates():
    c,s,p=setup((3,8))
    from generic_chess.core.search_runtime import SearchPathRuntime
    r=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses)
    seen=0
    for step in range(14):
        before=r.position
        for a in r.legal_actions():
            with r.pushed(a):
                for side in (0,1):assert p.in_check(r.position,side)==p.engine.in_check(r.position,side)
                assert p.has_legal_action(r.position)==p.engine.has_legal_action(r.position)
                seen+=1
            assert r.position==before
            assert p.has_legal_action(r.position)==p.engine.has_legal_action(r.position)
        actions=r.legal_actions()
        if not actions:break
        r.push(actions[step%len(actions)])
        if r.terminal_status.is_terminal:break
    assert seen>10


def test_overlapping_sources_remain_attacking_when_one_source_is_removed():
    c,s,p=setup((1,2));board=[None]*16
    for i,owner,tid in [(15,0,'K'),(0,1,'K'),(5,1,'A'),(7,1,'A')]:board[i]=Piece(owner,tid,tid)
    position=replace(s.state.position,board=tuple(board))
    data=p._prepare(position,None);without=data[4]
    # Enemy orthogonal sources5and7 both cover6. Removing5 must retain7's bit.
    assert data[3][1]&(1<<6) and without[1][5]&(1<<6)
    assert p.has_legal_action(position)==p.engine.has_legal_action(position)


def test_anchor_remove_effect_is_forbidden_even_on_a_geometrically_safe_landing():
    c,s,p=setup((1,2));board=[None]*16
    for i,owner,tid in [(5,1,'B'),(8,0,'K'),(9,1,'A'),(12,1,'K'),(13,0,'B'),(15,0,'A')]:board[i]=Piece(owner,tid,tid)
    position=replace(s.state.position,board=tuple(board),side_to_move=1)
    assert p.in_check(position,0) and p.in_check(position,1)
    assert p.engine.has_legal_action(position) is False
    assert p.has_legal_action(position) is False


def test_unsupported_and_noncanonical_state_uses_reference_without_guessing():
    rule=L.definition(1,2);ray=replace(rule,piece_types=rule.piece_types[:2]+(replace(rule.piece_types[2],movement_atoms=(RayAtom((1,0)),)),))
    c=L.compile_rule(ray);s=GameSession(c);p=PlainLeaperBooleans(c)
    assert not p.admitted
    assert p.in_check(s.state.position,0)==p.engine.in_check(s.state.position,0)
    assert p.has_legal_action(s.state.position)==p.engine.has_legal_action(s.state.position)
    assert p.metrics['fallbacks']==2
    c,s,p=setup();position=replace(s.state.position,aux_state=(((99,-1),True),))
    assert p.in_check(position,0)==p.engine.in_check(position,0)
    assert p.has_legal_action(position)==p.engine.has_legal_action(position)
    assert p.metrics['fallbacks']==2


def test_cancelled_prepare_never_publishes_partial_new_cache():
    c,s,p=setup();before=s.state.position
    assert p.has_legal_action(before)
    position=replace(before,side_to_move=1)
    count=0
    def stop():
        nonlocal count
        count+=1
        if count==4:raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):p.in_check(position,1,checkpoint=stop)
    assert p._position is before
    assert p.in_check(position,1)==p.engine.in_check(position,1)
    p.clear();assert p._position is None and p._data is None
