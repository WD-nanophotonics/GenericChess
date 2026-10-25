"""Research observer must preserve real terminal/cutoff/abort contracts."""
import pytest
from scripts.leaper_qclass_observer import QClassificationObserver
from generic_chess.ai.alphabeta import search as S
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from test_qsearch_correctness import _ctx, _evaluator, _king_rook_6, _check_chain_state
from test_qsearch_semantic_effects import transform_rules

@pytest.mark.parametrize('beta',[S.INF,0])
def test_observer_does_not_add_semantic_work_and_separates_unvisited(beta):
 c=compile_ruleset_for_execution(transform_rules(max_ply=1));state=GameSession(c).state
 results=[];saved=(SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions)
 for observe in(False,True):
  ctx=_ctx(c,_evaluator(c),SearchLimits(quiescence_max_depth=4,quiescence_hard_max_depth=8));ctx.runtime=SearchPathRuntime(state,c);ctx.runtime.attach_stats(ctx.stats)
  if observe:
   with QClassificationObserver()as obs:score=S.quiescence(state,-S.INF,beta,0,0,ctx)
   r=obs.result();assert r['counts'].get('quiet_rejected',0)==0
   assert all('cached_child_terminal'in e for e in r['details']if e['outcome'].endswith('_included'))
  else:score=S.quiescence(state,-S.INF,beta,0,0,ctx)
  ctx.runtime.assert_balanced();results.append((score,ctx.stats.qnodes,ctx.stats.runtime_pushes,ctx.stats.runtime_pops,ctx.stats.material_change_qactions))
 assert results[0]==results[1]
 assert saved==(SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions)

def test_observer_preserves_check_hard_abort_and_restores_wrappers():
 c=_king_rook_6();state=_check_chain_state(c);ctx=_ctx(c,_evaluator(c),SearchLimits(quiescence_max_depth=4,quiescence_hard_max_depth=4));ctx.runtime=SearchPathRuntime(state,c);ctx.runtime.attach_stats(ctx.stats)
 saved=(SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions)
 with QClassificationObserver()as obs:
  with pytest.raises(S.SearchAborted,match='^qsearch_check_hard_limit$'):S.quiescence(state,-S.INF,S.INF,0,4,ctx)
 assert obs.result()['counts']['q_aborted']==1
 assert obs.result()['counts']['frontier_not_generated']==1
 assert saved==(SearchPathRuntime.pushed,S.noisy_child,S._quiescence_runtime,S._order_qactions)
 ctx.runtime.assert_balanced()


def test_cutoff_observer_keeps_unvisited_distinct_from_quiet_rejected():
 from generic_chess.ai.evaluation.config import EvaluationConfig
 from generic_chess.ai.evaluation.evaluator import Evaluator
 from generic_chess.ai.evaluation.profile import build_ruleset_profile
 c=compile_ruleset_for_execution(transform_rules());state=GameSession(c).state
 cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0)
 ev=Evaluator(c,build_ruleset_profile(c,cfg),cfg)
 ctx=_ctx(c,ev,SearchLimits(max_nodes=4096,max_time_seconds=5));ctx.qdepth_limit=1;ctx.runtime=SearchPathRuntime(state,c);ctx.runtime.attach_stats(ctx.stats)
 with QClassificationObserver()as obs:score=S.quiescence(state,-S.INF,300,0,0,ctx)
 r=obs.result()['counts']
 assert score==300 and ctx.stats.qnodes==2
 assert r['ordinary:child_beta_cutoff']==1
 assert r['ordinary:child_beta_cutoff:unvisited']>0
 # Independent immutable successors define the lexical prefix before the
 # first noisy child. The fixture has preceding quiet king moves.
 from generic_chess.core.transition import legal_successors
 from generic_chess.ai.alphabeta.quiescence import classify_noisy
 pairs=sorted(legal_successors(state,c),key=lambda pair:str(pair[0]))
 noisy=classify_noisy(state,pairs,c)
 first=next(i for i,(a,_)in enumerate(pairs)if a in noisy)
 assert r['quiet_rejected']==first
 assert r['classifications']==first+1
 assert r['ordinary:child_beta_cutoff:visited']==first+1
 assert r['ordinary:child_beta_cutoff:unvisited']==len(pairs)-first-1
 ctx.runtime.assert_balanced()
