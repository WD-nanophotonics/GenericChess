"""One frozen H6 source witness: root-only Q interventions; no Player or solver."""
import argparse,json,time
from pathlib import Path
from scripts.research_record import record_value,write_record
from scripts.leaper_postexchange_source import sha,stamp,stopped
from scripts.leaper_check_extension_quality import record_interval
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.config import EvaluationConfig,MATE_SCORE
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts.leaper_pvs_quality_pilot import make_session


def bound(value,a,b):return 'UPPER' if value<=a else 'LOWER' if value>=b else 'EXACT'
def flip(b):return {'UPPER':'LOWER','LOWER':'UPPER','EXACT':'EXACT'}[b]


def root_intervention(alpha,beta,ctx,mode,trace):
 rt=ctx.runtime;state=rt.state;ctx.stats.qnodes+=1;ctx.budget.check(ctx.stats)
 term=rt.terminal_status
 if term.is_terminal:trace['source']='terminal';return S.terminal_score(term,state.position.side_to_move,0)
 decl=S._declaration_options(state,ctx.compiled,ctx.stats);win=next((x for x in decl if x.outcome=='WIN'),None);neutral=S._neutral_declaration(decl)
 trace['declarations']=record_value(decl)
 if win is not None:trace['source']='winning_declaration';return MATE_SCORE
 if neutral is not None:alpha=max(alpha,0)
 assert not rt.in_check(state.position.side_to_move,checkpoint=ctx.checkpoint),'candidate contract requires noncheck'
 keep_sp=mode=='ADD_QUIET'
 if keep_sp:
  sp=S._evaluate(state,ctx.evaluator,ctx);trace['standpat']=sp;ctx.budget.check(ctx.stats,force=True)
  if sp>=beta:trace['source']='standpat_cutoff';ctx.stats.stand_pat_cutoffs+=1;return max(sp,0) if neutral else sp
  if sp>alpha:alpha=sp;trace['source']='standpat'
  if S._ordinary_qdepth_limit(ctx)<=0:ctx.stats.qdepth_cutoffs+=1;trace['exit']='ordinary_qcap_before_legal';return alpha
 # NO_SP_* are explicit forced-one-root-step controls, including Q0. They
 # intentionally spend one legal ply; recursive children use unchanged Q.
 if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:raise S.SearchAborted('qsearch_budget')
 actions=S._runtime_legal_actions(ctx,ctx.checkpoint);ctx.budget.check(ctx.stats,force=True)
 actions=S._order_qactions(state,actions,0,ctx,in_check=False);trace['generated']=[record_value(a) for a in actions]
 side=state.position.side_to_move;enemies=S.enemy_board_count(state.position,side);inventory=S.material_inventory(state.position)
 for i,a in enumerate(actions):
  event=dict(action=record_value(a),alpha_before=alpha,beta=beta);trace['actions'].append(event)
  with rt.pushed(a,checkpoint=ctx.checkpoint):
   noisy=S.noisy_child(a,rt.state,side,enemies,inventory,lambda:rt.in_check(1-side,checkpoint=ctx.checkpoint),ctx.stats,capture_only=False,legacy_kind=None);event['noisy']=noisy
   if mode=='NO_SP_NOISY' and not noisy:event['disposition']='classified_quiet_skip';continue
   event['disposition']='entered';event['child_window']=[-beta,-alpha]
   raw=S._quiescence_runtime(-beta,-alpha,1,1,ctx);value=-raw
   event.update(raw_child_return=raw,child_bound=bound(raw,-beta,-alpha),negated_return=value,parent_bound=flip(bound(raw,-beta,-alpha)))
  if value>=beta:event['cutoff']=True;trace.update(source='child_cutoff',source_action=record_value(a),unvisited_after_cutoff=[record_value(x) for x in actions[i+1:]]);return value
  if value>alpha:alpha=value;trace.update(source='child',source_action=record_value(a));event['updated_alpha']=True
 trace.setdefault('source','neutral_declaration' if neutral is not None else 'inherited_alpha')
 return alpha


def root_snapshot(rt):
 return (rt.position,rt.ply_count,rt.terminal_status,tuple(rt.history),dict(rt.repetition_counts),rt.current_key,rt.search_key())


def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert sha(__file__)==p['source_sha256'];assert sha(p['candidate'])==p['candidate_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 begin=stamp();tick=time.perf_counter();rows=[];status='FAILED';failure=None
 try:
  candidate=json.loads(Path(p['candidate']).read_bytes());c,root=make_session(candidate);cfg=EvaluationConfig();profile,hit=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);ev=Evaluator(c,profile,cfg)
  assert record_value(profile)==json.loads(Path(p['profile']).read_bytes())['profile'];before=record_value(root.to_record())
  for first in p['first_main_iteration_complete']:
   for window in p['windows']:
    for mode in p['modes']:
     if [first,window,mode] in p.get('skip_consumed_slots',[]):continue
     if stopped() or time.perf_counter()-tick>=p['batch_seconds']:raise RuntimeError('frozen_batch_or_stop')
     a,b=window;rt=SearchPathRuntime.from_state(root.state,c,history_witnesses=root._search_witnesses);stats=SearchStatistics();limits=SearchLimits(max_depth=1,max_nodes=p['max_nodes'],max_time_seconds=p['query_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8)
     ctx=S._Context(c,ev,TranspositionTable(1),stats,S._Budget(limits,None),SearchTuning(),False,False,4,8,p['max_nodes'],runtime=rt,first_main_iteration_complete=first)
     snapshot=root_snapshot(rt)
     trace=dict(actions=[],entry_window=window,first_main_iteration_complete=first,mode=mode,forced_extra_root_ply=mode.startswith('NO_SP'),TT_enabled=False)
     qt=time.perf_counter();qs=stamp()
     try:
      value=S._quiescence_runtime(a,b,0,0,ctx) if mode=='BASELINE' else root_intervention(a,b,ctx,mode,trace)
      trace.update(status='RETURNED',value=value,bound_vs_original_entry=bound(value,a,b),child_perspective_negated=True)
     except S.SearchAborted as e:trace.update(status='ABORTED',reason=str(e),value=None)
     write_record(out/'latest-before-validation.json',trace)
     rt.assert_balanced();assert record_value(root.to_record())==before;assert root_snapshot(rt)==snapshot
     trace.update(stats=record_value(stats),seconds=time.perf_counter()-qt,started_at=qs,ended_at=stamp(),root_preserved=True)
     rows.append(trace);write_record(out/'queries.json',rows)
  status='CLOSED'
 except Exception as e:failure=type(e).__name__+':'+str(e);raise
 finally:
  result=dict(status=status,failure=failure,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=len(rows),new_Player_calls=0,new_games=0,new_solver=False,scope='Root-only counterfactual; all recursive children unchanged production Q; not old service controller or WDL proof')
  write_record(out/'summary.json',result);record_interval(begin,result['ended_at'],'research',str(out/'summary.json'),out);print(result)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
