"""Bounded observation of existing PVS dispatches, not an LMR implementation.

No new Core/evaluation calls occur inside the observer. Immutable parent/child
Positions and bounded action paths are classified offline after the search.
Attempted child dispatch, actual expansion and safely reducible work differ.
"""
import argparse
from collections import Counter
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.leaper_postexchange_source import load,replay,sha,stamp,stopped
from scripts.leaper_pvs_quality_pilot import make_session,digest
from scripts.leaper_check_extension_quality import record_interval
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json


class DispatchObserver:
    def __init__(self, original, limit=32):
        self.original=original;self.limit=limit;self.stack=[];self.samples=[]
        self.counts=Counter();self.discarded=0

    def __call__(self,*args,**kw):
        state,depth,alpha,beta,ply,ctx=args[:6]
        pv=kw.get('pv_node',True);previous=kw.get('prev_action')
        parent=self.stack[-1] if self.stack else None
        path=() if parent is None else parent['path']+((previous,) if previous is not None else ())
        frame=dict(depth=depth,ply=ply,pv=pv,position=ctx.runtime.position,path=path)
        sample=None
        self.counts['all_main_entries']+=1
        if parent and parent['depth']>=3 and parent['ply']>=1 and not parent['pv'] and not pv:
            caller=sys._getframe(1)
            if caller.f_code.co_name=='child_search' and caller.f_back is not None:
                # This is an observation of the current source, not a public API.
                loc=caller.f_back.f_locals
                assert loc.get('ctx') is ctx and loc.get('ply')==parent['ply']
                index=loc.get('move_index');assert type(index) is int
                if index>=4:
                    self.counts['late_nonPV_dispatches']+=1
                    if len(self.samples)<self.limit:
                        sample=dict(parent_depth=parent['depth'],parent_ply=parent['ply'],parent_pv=parent['pv'],
                                    child_depth=depth,child_pv=pv,move_index=index,alpha=alpha,beta=beta,
                                    parent_path=parent['path'],action=previous,parent_position=parent['position'],
                                    child_position=ctx.runtime.position,child_terminal=ctx.runtime.terminal_status,
                                    nodes_before=ctx.stats.nodes,successors_before=ctx.stats.successors_searched,
                                    tt_hits_before=ctx.stats.tt_hits)
                        self.samples.append(sample)
                    else:self.discarded+=1
        self.stack.append(frame)
        try:
            result=self.original(*args,**kw)
            if sample is not None:
                sample.update(status='RETURNED',score=result.score,
                              node_delta=ctx.stats.nodes-sample['nodes_before'],
                              successor_delta=ctx.stats.successors_searched-sample['successors_before'],
                              tt_hit_delta=ctx.stats.tt_hits-sample['tt_hits_before'])
            return result
        except BaseException as e:
            if sample is not None:sample.update(status='EXCEPTION',error_type=type(e).__name__,error=str(e))
            raise
        finally:
            assert self.stack.pop() is frame

    def classify(self,c):
        engine=semantic_engine_for(c)
        for x in self.samples:
            x['parent_in_check']=engine.in_check(x['parent_position'],x['parent_position'].side_to_move)
            # Classification uses copied actual child terminal status, not a
            # reconstructed guessed terminal or a stale mutable runtime view.
            parent=SimpleNamespace(position=x['parent_position'])
            child=SimpleNamespace(position=x['child_position'],terminal_status=x['child_terminal'])
            x['noisy']=bool(classify_noisy(parent,[(x['action'],child)],c))
            x['predicate_match']=not x['parent_in_check'] and not x['noisy'] and not x['child_terminal'].is_terminal
            x['immediate_TT_return_inferred']=(x.get('node_delta')==1 and x.get('successor_delta')==0 and x.get('tt_hit_delta',0)>0)
        return dict(counts=dict(self.counts),samples=record_value(self.samples),discarded=self.discarded,
                    coverage='BOUNDED_DISPATCH_PREFIX;not all nodes if discarded>0;not saved work or an LMR benefit',
                    predicate_matches=sum(x['predicate_match'] for x in self.samples),
                    matched_actual_expansions=sum(x['predicate_match'] and x.get('successor_delta',0)>0 for x in self.samples))


def work_signature(stats):
    return {k:v for k,v in record_value(stats).items()
            if not k.endswith('_seconds') and k not in ('time_to_first_legal_action','time_to_first_completed_iteration')}


def run(plan_path,out):
    plan=read_json(plan_path)
    for p,h in plan['files'].items():assert sha(p)==h
    assert sha(__file__)==plan['source_sha256']
    out.mkdir(exist_ok=False);write_record(out/'frozen.json',plan)
    roots={r['id']:r for r in load(plan['prepared'])['rows']};inputs=load(plan['selected'])
    original=S.negamax;start=time.perf_counter();results=[];halt=None
    for w in inputs:
        for arm in ('OFF1','ON','OFF2'):
            if stopped() or time.perf_counter()-start+plan['call_seconds']+2>=plan['batch_seconds']:
                halt='scoped_stop_or_dispatch_reserve';break
            begin=stamp();t=time.perf_counter();cpu=time.process_time()
            c,_=make_session(roots[w['case_id']]);s=replay(c,w['record'])
            p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
            rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=p.native_legality_provider,availability_provider=p.native_legality_provider.has_legal_action,check_provider=p.native_legality_provider.in_check)
            ctx=S._Context(c,p._evaluator,TranspositionTable(),SearchStatistics(),S._Budget(SearchLimits(max_nodes=plan['node_cap'],max_time_seconds=plan['call_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8),None),SearchTuning(use_pvs=True),True,True,4,8,None,runtime=rt,first_main_iteration_complete=True)
            observer=DispatchObserver(original,plan['sample_limit']);q=dict(family=w['family'],case_id=w['case_id'],arm=arm,requested_depth=plan['depth'],record_sha256=digest(s.to_record()),constructor_seconds=time.perf_counter()-t)
            search_tick=time.perf_counter();search_cpu=time.process_time()
            try:
                if arm=='ON':S.negamax=observer
                r=S.negamax(rt.state,plan['depth'],-S.INF,S.INF,0,ctx)
                q.update(status='RETURNED',result=record_value(r))
            except S.SearchAborted as e:q.update(status='ABORTED_UNKNOWN',reason=str(e))
            finally:
                S.negamax=original
            q.update(search_seconds=time.perf_counter()-search_tick,search_cpu_seconds=time.process_time()-search_cpu,
                     outer_seconds=time.perf_counter()-t,outer_cpu_seconds=time.process_time()-cpu,
                     stats=record_value(ctx.stats),work_signature=work_signature(ctx.stats))
            rt.assert_balanced();assert not observer.stack and digest(s.to_record())==q['record_sha256']
            q['runtime_balanced']=True;q['global_restored']=S.negamax is original
            # End the execution/measurement interval BEFORE offline classification.
            q['ended_at']=stamp();q['started_at']=begin
            write_record(out/f"query-{w['family']}-{arm}.json",q)
            record_interval(begin,q['ended_at'],'analysis',str(out/f"query-{w['family']}-{arm}.json"),out)
            if arm=='ON':
                v=stamp();q['observation']=observer.classify(c);write_record(out/f"samples-{w['family']}.json",q['observation']);record_interval(v,stamp(),'analysis',str(out/f"samples-{w['family']}.json"),out)
            results.append(q);write_record(out/'returns.json',results)
            print(dict(family=w['family'],arm=arm,status=q['status'],seconds=q['search_seconds'],samples=len(observer.samples)),flush=True)
        if halt:break
    triads=[]
    for w in inputs:
        group=[q for q in results if q['family']==w['family']]
        complete=len(group)==3 and all(q['status']=='RETURNED' for q in group)
        parity=complete and all(q['result']==group[0]['result'] and q['work_signature']==group[0]['work_signature'] for q in group)
        ratio=group[1]['search_seconds']/((group[0]['search_seconds']+group[2]['search_seconds'])/2) if parity else None
        triads.append(dict(family=w['family'],complete=complete,parity=parity,observer_bracket_wall_ratio=ratio,
                           matches=next((q.get('observation',{}).get('predicate_matches',0) for q in group if q['arm']=='ON'),0)))
    summary=dict(planned_queries=len(inputs)*3,queries=len(results),NOT_RUN=len(inputs)*3-len(results),triads=triads,halt=halt,
                 qualified_source_families=[x['family'] for x in triads if x['parity'] and x['observer_bracket_wall_ratio']<=1.10 and x['matches']>0],
                 claim='Observer feasibility only;PVS existing policy,LMR NOT_IMPLEMENTED;no actual gain or safety/strength proof',new_choose_action_calls=0,new_games=0)
    write_record(out/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
