"""The attribution adapter must consume full terminal/state authority."""
from dataclasses import replace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.native.compiler import NativeUnsupportedRuleError
from scripts.search_backend_comparison import CASES,CoreBoard,VALUES,minimal_ab
from scripts.native_backend_bridge import NativeBoard,audit_native_tree
from native_test_helpers import requires_native

pytestmark=requires_native


def test_native_bridge_preserves_ep_aux_history_and_fixed_work_trace():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    core=CoreBoard(CASES[3],compiled)
    native=NativeBoard(core,VALUES['chess'])
    assert audit_native_tree(core,native,1)>1
    left=minimal_ab(core,2,seconds=10,node_limit=4096,trace=True)
    right=minimal_ab(native,2,seconds=10,node_limit=4096,trace=True)
    for key in ('move','score','work','reason','trace_sha256'):
        assert left[key]==right[key]
    assert core.restored() and native.restored()


@pytest.mark.parametrize('checker',[0,1])
def test_native_bridge_scores_legally_replayed_continuous_check(checker):
    rules=replace(build_builtin_ruleset('standard_shogi'),stalemate_result='draw')
    compiled=compile_ruleset_for_execution(rules)
    setup,cycle=(('4k4/3R5/9/9/9/9/9/9/8K b - 1','6b5b 5a6a 5b6b 6a5a')
                 if checker==0 else ('k8/9/9/9/9/9/9/5r3/4K4 w - 1','4h5h 5i4i 5h4h 4i5i'))
    core=CoreBoard(dict(game='shogi',setup=setup,moves=' '.join([cycle]*3)),compiled)
    native=NativeBoard(core,VALUES['shogi'])
    assert core.initial.terminal_status.winner==1-checker
    assert audit_native_tree(core,native,0)==1
    assert native.terminal(3)==core.terminal(3)==-MATE_SCORE+3
    result=minimal_ab(native,1,seconds=10)
    assert result['score']==-MATE_SCORE
    assert result['move'] is None and result['work']['nodes']==1


def test_native_bridge_does_not_hide_v4_stalemate_loss_gap():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    core=CoreBoard(CASES[5],compiled)
    with pytest.raises(NativeUnsupportedRuleError,match='stalemate loss'):
        NativeBoard(core,VALUES['shogi'])


@pytest.mark.parametrize('checker',[0,1])
def test_native_bridge_propagates_perpetual_winner_from_child_before_leaf(checker):
    rules=replace(build_builtin_ruleset('standard_shogi'),stalemate_result='draw')
    compiled=compile_ruleset_for_execution(rules)
    setup,cycle=(('4k4/3R5/9/9/9/9/9/9/8K b - 1','6b5b 5a6a 5b6b 6a5a')
                 if checker==0 else ('k8/9/9/9/9/9/9/5r3/4K4 w - 1','4h5h 5i4i 5h4h 4i5i'))
    moves=(cycle+' '+cycle+' '+cycle).split()
    core=CoreBoard(dict(game='shogi',setup=setup,moves=' '.join(moves[:-1])),compiled)
    native=NativeBoard(core,VALUES['shogi'])
    assert core.terminal(0) is None
    assert audit_native_tree(core,native,1)>1
    for board in (core,native):
        terminal_reply=dict(board.actions())[moves[-1]]
        board.push(terminal_reply)
        try:
            assert board.terminal(1)==-MATE_SCORE+1
        finally:
            board.pop()
    left=minimal_ab(core,1,seconds=10,trace=True)
    right=minimal_ab(native,1,seconds=10,trace=True)
    for key in ('move','score','work','reason','trace_sha256'):
        assert left[key]==right[key]
    assert right['score']==MATE_SCORE-1
    assert core.restored() and native.restored()


@pytest.mark.parametrize('tt_megabytes',[0,64])
def test_native_default_selected_action_matches_exact_child_value(tt_megabytes):
    from generic_chess.native.semantic_engine import SemanticSearchEngine
    from generic_chess.native.semantic import semantic_iterative_search,make_checked,public_action
    from generic_chess.session.session import GameSession
    from generic_chess.ai.limits import SearchLimits
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    core=CoreBoard(CASES[3],compiled)
    native=NativeBoard(core,VALUES['chess'])
    session=GameSession(compiled)
    session._state=core.initial
    session._search_history_witnesses=core.witnesses
    engine=SemanticSearchEngine(compiled,native.native,board_values=VALUES['chess'],
        hand_values=VALUES['chess'],tt_megabytes=tt_megabytes)
    for _ in range(2):  # Cold, then reused persistent TT under unchanged semantics.
        result=engine.search(session,
            SearchLimits(max_depth=3,max_nodes=100000,max_time_seconds=10,quiescence_max_depth=0))
        assert result.completed_depth==3 and not result.root_window_pruning
        selected=dict((public_action(native.native,raw),raw) for _,raw in native.actions())[result.action]
        child=semantic_iterative_search(native.native,make_checked(native.native,native.position,selected),
            2,max_nodes=100000,max_time_seconds=10,board_values=VALUES['chess'],
            hand_values=VALUES['chess'],_root_ply_offset=1)
        assert child['completed_depth']==2
        assert result.score==-child['score']==100
        assert native.restored() and core.restored() and session.state==core.initial
