"""A true one-ply rule terminal may end an explicitly requested decision search."""
import pytest
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules, NativeUnsupportedRuleError
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.core.transition import apply_action
from test_native_terminal_declaration_priority import position

pytestmark = pytest.mark.skipif(not native_available(), reason='Native unavailable')

def make(session, tt=0):
    nr=compile_native_semantic_rules(session.compiled)
    values={t:0 if m.is_anchor else 100 for t,m in session.compiled.support.type_metadata.items()}
    return SemanticSearchEngine(session.compiled,nr,board_values=values,hand_values=values,
                                tt_megabytes=tt,ordering_cache_enabled=False)

@pytest.mark.parametrize('window',[False,True])
@pytest.mark.parametrize('tt',[0,1])
@pytest.mark.parametrize('q',[0,4])
def test_physical_mate_goal_and_analysis_are_distinct(window,tt,q):
    s=position();e=make(s,tt);before=s.state,s.to_record(),s._search_witnesses
    lim=SearchLimits(max_depth=2,max_time_seconds=5,quiescence_max_depth=q)
    # A real persistent table switches objectives both ways, without clearing.
    for goal in [False,True,False,True]:
        r=e.search(s,lim,root_window_pruning=window,stop_on_immediate_win=goal)
        assert r.action is not None and r.declaration_id is None
        child=apply_action(s.state,r.action,s.compiled)
        assert child.terminal_status.is_terminal and child.terminal_status.winner==s.state.position.side_to_move
        assert r.completed_depth==(0 if goal else 2)
        assert r.immediate_win is goal
        assert r.result_source == ("verified_root_child" if goal else "main_iteration")
        if goal:
            assert r.termination_reason=='root_immediate_win'
            assert r.result_ordinary_qdepth is None and r.result_check_hard_qdepth is None
        assert before==(s.state,s.to_record(),s._search_witnesses)

@pytest.mark.parametrize('window',[False,True])
@pytest.mark.parametrize('kind',['draw','declaration'])
def test_rule_draw_and_declaration_do_not_become_physical_goal(window,kind):
    s=position(max_ply=1) if kind=='draw' else position(declaring_owner=0)
    r=make(s).search(s,SearchLimits(max_depth=2,max_time_seconds=5),
                     root_window_pruning=window,stop_on_immediate_win=True)
    assert not r.immediate_win
    assert r.completed_depth==2
    if kind=='draw':assert r.score==0 and r.declaration_id is None
    else:assert r.declaration_id=='win' and r.action is None

@pytest.mark.parametrize('stop',['cancel','nodes','zero_depth'])
def test_stopped_or_unsearched_root_never_claims_goal(stop):
    s=position();token=CancellationToken()
    if stop=='cancel':token.cancel()
    lim=SearchLimits(max_depth=0 if stop=='zero_depth'else 4,
                     max_nodes=0 if stop=='nodes'else None,max_time_seconds=5)
    r=make(s).search(s,lim,token,stop_on_immediate_win=True)
    assert r.completed_depth==0 and not r.immediate_win
    if stop=='cancel':assert r.termination_reason=='cancelled'
    elif stop=='nodes':assert r.termination_reason=='node_budget'

@pytest.mark.parametrize('value',[1,None,'yes'])
def test_goal_flag_is_explicit_bool(value):
    s=position()
    with pytest.raises(TypeError,match='stop_on_immediate_win'):
        make(s).search(s,SearchLimits(max_depth=1),stop_on_immediate_win=value)

def test_missing_goal_capability_requires_rebuild_but_default_analysis_works(monkeypatch):
    s=position();e=make(s);real=e._backend.native_capabilities
    monkeypatch.setattr(e._backend,'native_capabilities',lambda:{**real(),'semantic_immediate_win_goal':False})
    with pytest.raises(NativeUnsupportedRuleError,match='immediate-win'):
        e.search(s,SearchLimits(max_depth=1),stop_on_immediate_win=True)
    assert e.search(s,SearchLimits(max_depth=1)).completed_depth==1

@pytest.mark.parametrize('window',[False,True])
@pytest.mark.parametrize('offset',[0,1])
def test_one_shot_goal_keeps_actual_mate_distance_and_state(window,offset):
    from generic_chess.native import semantic as sem
    from generic_chess.native.adapter import pack_semantic_search_position
    s=position();nr=compile_native_semantic_rules(s.compiled)
    pos=pack_semantic_search_position(s.compiled,nr,s);before=sem.snapshot(nr,pos)
    r=sem.semantic_iterative_search(nr,pos,3,root_window_pruning=window,
        stop_on_immediate_win=True,_root_ply_offset=offset,max_time_seconds=5)
    assert r['immediate_win'] and r['completed_depth']==0
    assert r['score']==100_000_000-1-offset and r['result_source']=='verified_root_child'
    action=sem.public_action(nr,r['best_action'])
    assert apply_action(s.state,action,s.compiled).terminal_status.winner==s.state.position.side_to_move
    assert sem.snapshot(nr,pos)==before

@pytest.mark.parametrize('outcome',['NO_CONTEST','RESTART'])
def test_opponent_neutral_option_is_not_a_physical_win(outcome):
    from dataclasses import replace
    from test_no_contest_search import defender_root,neutral,compile_session
    from conftest import make_ruleset,king_type,T
    from generic_chess.core.movement import RayAtom
    old=defender_root()
    rook=T('R',RayAtom((0,1)),RayAtom((0,-1)),RayAtom((1,0)),RayAtom((-1,0)))
    rules=replace(make_ruleset(4,[king_type(),rook],lines=['....','...R','....','.k.K']),
                  declarations=(neutral(1,outcome),))
    s=compile_session(rules)
    # Preserve the real held-piece state and complete one-entry history.
    from generic_chess.core.identity import position_identity_key
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.terminal import terminal_result
    p=replace(old.state.position,ruleset_fingerprint=s.compiled.ruleset_fingerprint)
    key=position_identity_key(p,s.compiled)
    st=replace(s.state,position=p,history=(HistoryRecord(key,-1,'',False),),repetition_counts=((key,1),))
    s._state=replace(st,terminal_status=terminal_result(st,s.compiled));s._search_history_witnesses=(p,)
    before=s.to_record()
    r=make(s,1).search(s,SearchLimits(max_depth=2,max_time_seconds=5,quiescence_max_depth=2),
                       root_window_pruning=True,stop_on_immediate_win=True)
    assert not r.immediate_win and r.score==0
    assert before==s.to_record()

@pytest.mark.parametrize('checker',[0,1])
def test_actual_perpetual_check_terminal_uses_complete_played_history(checker):
    from dataclasses import replace
    from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from scripts.search_backend_comparison import CoreBoard
    c=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),stalemate_result='draw'))
    setup,cycle=('4k4/3R5/9/9/9/9/9/9/8K b - 1','6b5b 5a6a 5b6b 6a5a')if checker==0 else('k8/9/9/9/9/9/9/5r3/4K4 w - 1','4h5h 5i4i 5h4h 4i5i')
    core=CoreBoard(dict(game='shogi',setup=setup,moves=' '.join((cycle.split()*3)[:-1])),c)
    s=GameSession(c);s._state=core.initial;s._search_history_witnesses=core.witnesses
    e=make(s);before=s.to_record(),s._search_witnesses
    r=e.search(s,SearchLimits(max_depth=3,max_time_seconds=5),stop_on_immediate_win=True)
    assert r.immediate_win and r.completed_depth==0 and r.termination_reason=='root_immediate_win'
    child=apply_action(s.state,r.action,c)
    assert child.terminal_status.status.value=='perpetual_check' and child.terminal_status.winner==1-checker
    assert before==(s.to_record(),s._search_witnesses)

@pytest.mark.parametrize('nodes,proved,reason',[
    (12,False,'node_budget'),(13,True,'node_budget'),(14,True,'root_immediate_win'),
])
def test_completed_physical_child_survives_coincident_node_stop(nodes,proved,reason):
    s=position();before=s.to_record(),s._search_witnesses
    r=make(s).search(s,SearchLimits(max_depth=2,max_nodes=nodes),stop_on_immediate_win=True)
    assert r.completed_depth==0 and r.result_ordinary_qdepth is None
    assert r.immediate_win is proved and r.termination_reason==reason
    assert r.used_fallback is not proved
    assert r.result_source==('verified_root_child'if proved else'fallback')
    if proved:
        child=apply_action(s.state,r.action,s.compiled)
        assert child.terminal_status.is_terminal and child.terminal_status.winner==s.state.position.side_to_move
    assert before==(s.to_record(),s._search_witnesses)

def test_raw_non_bool_goal_rejection_releases_engine_and_keeps_position():
    from generic_chess.native.adapter import pack_semantic_search_position
    s=position();e=make(s,1);pos=pack_semantic_search_position(s.compiled,e._native_rules,s)
    with pytest.raises(TypeError,match='stop_on_immediate_win'):
        e._backend.semantic_engine_search(e._capsule,pos,1,
            None,None,None,None,False,False,0,0,None,1)
    # Reuse the same real engine after its nested C parser rejected the value.
    r=e.search(s,SearchLimits(max_depth=1))
    assert r.completed_depth==1 and not r.immediate_win
