"""Same complete qsearch values, different action traversal and early cutoffs."""
from dataclasses import replace
import pytest
from test_qsearch_correctness import _ctx, _evaluator, _king_rook_6, _check_chain_state
from generic_chess.ai.alphabeta.search import INF, quiescence, _order_qactions, SearchAborted
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_target_square

def test_default_is_off_and_ordering_disabled_preserves_lexical():
    c=_king_rook_6();s=_check_chain_state(c)
    ctx=_ctx(c,_evaluator(c),SearchLimits(quiescence_max_depth=1,quiescence_hard_max_depth=8))
    assert not SearchTuning().use_ordered_qsearch
    actions=[a for a,_ in legal_successors(s,c)]
    assert _order_qactions(s,actions,0,ctx)==sorted(actions,key=str)
    ctx.tuning=replace(ctx.tuning,use_ordered_qsearch=True);ctx.use_ordering=False
    assert _order_qactions(s,actions,0,ctx)==sorted(actions,key=str)

def test_ordering_retains_all_evasions_and_prioritizes_capture():
    c=_king_rook_6();s=_check_chain_state(c)
    ctx=_ctx(c,_evaluator(c),SearchLimits(quiescence_max_depth=1,quiescence_hard_max_depth=8))
    ctx.tuning=replace(ctx.tuning,use_ordered_qsearch=True)
    actions=[a for a,_ in legal_successors(s,c)]
    ordered=_order_qactions(s,actions,0,ctx)
    assert set(ordered)==set(actions) and len(ordered)==len(actions)
    target=action_target_square(ordered[0]);piece=s.position.board[target.rank*6+target.file]
    assert piece is not None and piece.owner!=s.position.side_to_move

@pytest.mark.parametrize('qdepth',[0,1,2])
def test_complete_full_window_value_parity(qdepth):
    c=_king_rook_6();s=_check_chain_state(c)
    limits=SearchLimits(max_nodes=100000,quiescence_max_depth=qdepth,quiescence_hard_max_depth=8)
    a=_ctx(c,_evaluator(c),limits);b=_ctx(c,_evaluator(c),limits)
    b.tuning=replace(b.tuning,use_ordered_qsearch=True)
    assert quiescence(s,-INF,INF,0,0,a)==quiescence(s,-INF,INF,0,0,b)
    assert a.stats.in_check_qnodes and b.stats.in_check_qnodes

def test_ordering_keeps_hard_check_abort():
    c=_king_rook_6();s=_check_chain_state(c)
    ctx=_ctx(c,_evaluator(c),SearchLimits(quiescence_max_depth=0,quiescence_hard_max_depth=0))
    ctx.tuning=replace(ctx.tuning,use_ordered_qsearch=True)
    with pytest.raises(SearchAborted,match='qsearch_check_hard_limit'):
        quiescence(s,-INF,INF,0,0,ctx)

def test_capture_only_excludes_quiet_check_but_keeps_actual_captures():
    from generic_chess.ai.alphabeta.quiescence import classify_noisy
    from ai_fixtures import build_4x4_rooks
    from conftest import make_state
    from generic_chess.core.actions import action_source_square
    c=build_4x4_rooks();s=make_state(c,['..k.','....','R.r.','K...'])
    successors=list(legal_successors(s,c))
    full=classify_noisy(s,successors,c)
    captures=classify_noisy(s,successors,c,capture_only=True)
    assert set(captures)<set(full)
    assert captures
    for action in captures:
        target=action_target_square(action)
        occupant=s.position.board[target.rank*4+target.file]
        assert occupant is not None and occupant.owner!=s.position.side_to_move

def test_capture_only_preserves_en_passant_and_promotion():
    from generic_chess.ai.alphabeta.quiescence import classify_noisy
    import scripts.chess_development as d
    c=d.compile_ruleset_for_execution(d.build_western_chess_ruleset())
    for fen,required in [('7k/8/8/3pP3/8/8/8/K7 w - d6 0 1',{'e5d6'}),
                         ('7k/P7/8/8/8/8/8/7K w - - 0 1',{'a7a8q','a7a8r','a7a8b','a7a8n'})]:
        s=d.root_from_fen(fen,c)
        noisy=classify_noisy(s,list(legal_successors(s,c)),c,capture_only=True)
        assert required <= {d.uci(a) for a in noisy}

def test_capture_only_keeps_quiet_terminal_mate():
    from generic_chess.ai.alphabeta.quiescence import classify_noisy
    import scripts.chess_development as d
    c=d.compile_ruleset_for_execution(d.build_western_chess_ruleset())
    s=d.root_from_fen('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1',c)
    successors=list(legal_successors(s,c))
    quiet_terminal=[a for a,child in successors if child.terminal_status.is_terminal
                    and s.position.board[action_target_square(a).rank*8+action_target_square(a).file] is None]
    assert quiet_terminal
    noisy=classify_noisy(s,successors,c,capture_only=True)
    assert set(quiet_terminal)<=set(noisy)

def test_capture_only_does_not_filter_check_evasions():
    c=_king_rook_6();s=_check_chain_state(c)
    limits=SearchLimits(max_nodes=100000,quiescence_max_depth=0,quiescence_hard_max_depth=8)
    a=_ctx(c,_evaluator(c),limits);b=_ctx(c,_evaluator(c),limits)
    b.tuning=replace(b.tuning,use_ordered_qsearch=True,use_capture_only_qsearch=True)
    assert quiescence(s,-INF,INF,0,0,a)==quiescence(s,-INF,INF,0,0,b)
    assert b.stats.in_check_qnodes>0

@pytest.mark.parametrize('qdepth,capture_only',[(0,False),(2,True)])
@pytest.mark.parametrize('reason',['time_limit','node_limit','qsearch_budget'])
def test_aborted_iteration_keeps_last_complete_root(monkeypatch,qdepth,capture_only,reason):
    import generic_chess.ai.alphabeta.search as search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    import scripts.chess_development as d
    c=d.compile_ruleset_for_execution(d.build_western_chess_ruleset())
    s=d.root_from_fen('7k/8/8/3pP3/8/8/8/K7 w - d6 0 1',c)
    original=search.negamax;finished=[]
    def interrupt(state,depth,alpha,beta,ply,ctx,**kwargs):
        if ply==0 and depth==2:
            raise SearchAborted(reason)
        result=original(state,depth,alpha,beta,ply,ctx,**kwargs)
        if ply==0:finished.append(result)
        return result
    monkeypatch.setattr(search,'negamax',interrupt)
    stats=SearchStatistics()
    result=search.run_root_search(s,c,d.evaluator('unit'),TranspositionTable(),
        SearchLimits(max_depth=3,max_nodes=100000,quiescence_max_depth=qdepth,quiescence_hard_max_depth=8),None,stats,
        use_tt=True,use_ordering=True,tuning=SearchTuning(use_root_tactical=False,use_pvs=True,use_ordered_qsearch=True,use_capture_only_qsearch=capture_only,use_check_only_qsearch=qdepth==0))
    assert len(finished)==1 and stats.completed_depth==1
    assert result==(finished[0].best_action,finished[0].score,finished[0].pv,reason)

@pytest.mark.parametrize('fen',[
    '3k4/2p5/8/8/8/8/8/3R3K w - - 0 1',
    '7k/8/8/3pP3/8/8/8/K7 w - d6 0 1',
])
@pytest.mark.parametrize('capture_only',[False,True])
def test_native_and_author_complete_root_scores_agree(fen,capture_only):
    from scripts.chess_development import compare_case
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.western_chess import build_western_chess_ruleset
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    provider=NativeSemanticLegalityProvider.try_create(c,strict=True)
    if provider is None:pytest.skip('optional native unavailable')
    from scripts.chess_development import root_from_fen, iter_legal_actions, uci
    first=next(iter(iter_legal_actions(root_from_fen(fen,c),c)))
    case=dict(id='qorder-scope',fen=fen,accepted_uci=[uci(first)],answer_basis='arbitrary legal integration marker, not oracle')
    limits=SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=10,quiescence_max_depth=1,quiescence_hard_max_depth=8)
    a=compare_case(case,c,limits,ordering=True,use_tt=True,tuning=SearchTuning(use_root_tactical=False,use_pvs=True,use_capture_only_qsearch=capture_only))
    b=compare_case(case,c,limits,ordering=True,use_tt=True,tuning=SearchTuning(use_root_tactical=False,use_pvs=True,use_ordered_qsearch=True,use_capture_only_qsearch=capture_only))
    n=compare_case(case,c,limits,provider=provider,ordering=True,use_tt=True,tuning=SearchTuning(use_root_tactical=False,use_pvs=True,use_ordered_qsearch=True,use_capture_only_qsearch=capture_only))
    assert all(r['completed'] for report in (a,b,n) for r in report['rows'])
    assert [r['score'] for r in a['rows']]==[r['score'] for r in b['rows']]==[r['score'] for r in n['rows']]
