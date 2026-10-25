from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_anchor_mandatory_q import AnchorMandatoryQ
from tests.development.test_leaper_forced_quiet_q import context,call
from generic_chess.ai.alphabeta import search as S

def test_mandatory_single_anchor_reaches_actual_clock():
    _,ctx=context();ctx.qdepth_limit=4
    with AnchorMandatoryQ()as p:assert call(ctx)==0 and p.counts['anchor_frontiers']==1
    ctx.runtime.assert_balanced()

@pytest.mark.parametrize('kind',['q0','reserve','hard'])
def test_reserved_and_explicit_q0_and_hard_boundary_unchanged(kind):
    _,ctx=context();ctx.qdepth_limit=4
    if kind=='q0':ctx.qdepth_limit=0
    elif kind=='reserve':ctx.first_main_iteration_complete=False
    else:ctx.qhard_depth_limit=0
    with AnchorMandatoryQ()as p:assert call(ctx)==4242 and not p.counts
    ctx.runtime.assert_balanced()

def test_existing_qbudget_aborts_and_restores_runtime():
    _,ctx=context(qcap=1);ctx.qdepth_limit=4;old=S._quiescence_runtime
    with pytest.raises(S.SearchAborted,match='qsearch_budget'):
        with AnchorMandatoryQ():call(ctx)
    assert S._quiescence_runtime is old;ctx.runtime.assert_balanced()


def test_branching_anchor_frontier_is_not_singleton_fallback():
    from generic_chess.core.search_runtime import SearchPathRuntime
    _,ctx=context();king=ctx.compiled.types_by_id['K'];board=[[None]*5 for _ in range(5)];board[0][0]=L.Piece(0,'K','K');board[4][4]=L.Piece(1,'K','K')
    r=L.RuleSet(board_size=5,piece_types=(king,),initial_position=tuple(tuple(x)for x in board),drop_allowed={},capture_disposition='remove_from_game',max_ply=1,repetition_limit=4);c=L.compile_rule(r);ss=L.GameSession(c);assert len(ss.legal_actions())==3
    ctx.compiled=c;ctx.runtime=SearchPathRuntime.from_state(ss.state,c);ctx.qdepth_limit=4
    with AnchorMandatoryQ()as p:assert call(ctx)==0 and p.counts['branching_anchor_frontiers']==1 and p.counts['anchor_actions']==3
    ctx.runtime.assert_balanced()
