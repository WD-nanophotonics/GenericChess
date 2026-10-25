"""Actual Core singleton quiet frontier and safety boundaries."""
from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_forced_quiet_q import ForcedQuietQ
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
class Fixed:
    def evaluate(self,state):return 4242

def context(*,clock=1,hard=8,qcap=None,cancel=None,first=None):
    king=L.PieceType('K','K',tuple(L.LeapAtom(v)for v in L.offsets(3)),is_anchor=True)
    rule=L.RuleSet(board_size=3,piece_types=(king,),initial_position=((L.Piece(0,'K','K'),None,L.Piece(1,'K','K')),(None,None,None),(None,None,None)),drop_allowed={},capture_disposition='remove_from_game',max_ply=clock,repetition_limit=4)
    c=L.compile_rule(rule);s=L.GameSession(c);assert len(s.legal_actions())==1
    lim=SearchLimits(max_nodes=1000,quiescence_max_depth=0,quiescence_hard_max_depth=hard)
    rt=SearchPathRuntime.from_state(s.state,c)
    ctx=S._Context(c,Fixed(),TranspositionTable(),SearchStatistics(),S._Budget(lim,cancel),SearchTuning(),True,True,0,hard,qcap,runtime=rt,first_main_iteration_complete=first)
    return s,ctx

def call(ctx):return S.quiescence(ctx.runtime.state,-S.INF,S.INF,0,0,ctx)

def test_actual_singleton_quiet_clock_draw_overrides_fictional_pass():
    s,ctx=context();assert not ctx.runtime.in_check(0);s.submit(s.legal_actions()[0]);assert s.result.winner is None and s.result.status.value=='max_ply'
    assert call(ctx)==4242
    with ForcedQuietQ()as p:assert call(ctx)==0 and p.counts['forced']==1
    ctx.runtime.assert_balanced()

@pytest.mark.parametrize('kw',[dict(hard=0),dict(first=False)])
def test_hard_limit_and_first_reserve_keep_original_path(kw):
    _,ctx=context(**kw)
    with ForcedQuietQ()as p:assert call(ctx)==4242 and not p.counts
    ctx.runtime.assert_balanced()

def test_qnode_cap_remains_authoritative():
    _,ctx=context(qcap=1);old=S._quiescence_runtime
    with pytest.raises(S.SearchAborted,match='qsearch_budget'):
        with ForcedQuietQ():call(ctx)
    assert S._quiescence_runtime is old;ctx.runtime.assert_balanced()

def test_cancel_precedes_new_frontier():
    class Cancel:
        def is_cancelled(self):return True
    _,ctx=context(cancel=Cancel())
    with pytest.raises(S.SearchAborted,match='cancelled'):
        with ForcedQuietQ()as p:call(ctx)
    assert not p.counts;ctx.runtime.assert_balanced()
