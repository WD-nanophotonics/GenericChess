"""Research-only LMR: signs, known selectivity risk and actual Core rollback."""
from types import SimpleNamespace
from pathlib import Path
import gzip,json
import pytest
from scripts.leaper_lmr_research_policy import LateQuietReduction
from scripts.leaper_pvs_quality_pilot import make_session,digest
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime


class ForcedPredicate(LateQuietReduction):
    def _eligible(self,*a):return True


@pytest.mark.parametrize('reduced,expected_depths,expected_score',[(5,[1],5),(-5,[1,2],-10)])
def test_child_sign_research_and_preserved_actual_ply(reduced,expected_depths,expected_score):
    calls=[]
    def original(state,depth,alpha,beta,ply,ctx,**kw):
        calls.append((depth,alpha,beta,ply))
        return SimpleNamespace(score=reduced if depth==1 else -10)
    ctx=SimpleNamespace(runtime=SimpleNamespace(position=object()),budget=SimpleNamespace(check=lambda *a,**k:None),stats=object())
    p=ForcedPredicate(original)
    got=p(None,2,-1,0,2,ctx,pv_node=False)
    assert [x[0] for x in calls]==expected_depths and got.score==expected_score
    assert all(x[1:]==(-1,0,2) for x in calls) and not p.stack
    # The first case deliberately exposes the known heuristic risk: the
    # unvisited full-depth value would improve the parent, but is not searched.
    if reduced==5:assert p.counts['reduced_fail_low_kept']==1


@pytest.fixture(scope='module')
def packet():return json.loads(gzip.decompress(Path('docs/research/data/leaper_quiet_source_20261028/inputs.json.gz').read_bytes()))


def context(row,cancel=None):
    c,s=make_session(row);p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
    provider=p.native_legality_provider
    rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
    ctx=S._Context(c,p._evaluator,TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=1000000,max_time_seconds=5,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel),SearchTuning(use_pvs=True),True,True,4,8,None,runtime=rt,first_main_iteration_complete=True)
    return c,s,ctx


def test_actual_cancel_after_first_reduction_unwinds_and_stores_no_root_exact(packet):
    class Stop:
        policy=None
        def is_cancelled(self):return self.policy is not None and self.policy.counts['reductions']>0
    token=Stop();c,s,ctx=context(next(x for x in packet['rows'] if x['family']==1),token)
    before=digest(s.to_record());key=ctx.runtime.search_key();original=S.negamax;policy=LateQuietReduction(original);token.policy=policy
    try:
        S.negamax=policy
        with pytest.raises(S.SearchAborted,match='cancelled'):S.negamax(ctx.runtime.state,4,-S.INF,S.INF,0,ctx)
    finally:S.negamax=original
    assert policy.counts['reductions']>0 and not policy.stack
    ctx.runtime.assert_balanced();assert digest(s.to_record())==before and ctx.runtime.search_key()==key
    assert ctx.tt.probe(key) is None


@pytest.mark.parametrize('index',range(16))
def test_actual_terminal_clock_children_cannot_be_reduced(packet,index):
    c,s,ctx=context(packet['clock_rows'][index]);original=S.negamax;p=LateQuietReduction(original)
    try:
        S.negamax=p;r=S.negamax(ctx.runtime.state,4,-S.INF,S.INF,0,ctx)
    finally:S.negamax=original
    assert r.score==0 and p.counts['reductions']==0 and r.best_action in s.legal_actions()
    assert not p.stack;ctx.runtime.assert_balanced()
