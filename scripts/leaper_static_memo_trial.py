"""Frozen static-memo shadow census and conditional fixed-work cost assessment."""
import argparse,gzip,json,time
from pathlib import Path
from scripts.leaper_exact_static_memo import ExactStaticMemo
from scripts.leaper_qscan_cost_feasibility import Cancel,signature
from scripts.leaper_quiet_root_intervention import S,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,EvaluationConfig,EvaluationProfileCache,Evaluator,make_session,record_value,write_record,sha,stamp,stopped,record_interval
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider


def call(row,mode,slot,p,out):
 c,s=make_session(row);cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(c,profile,cfg);provider=NativeSemanticLegalityProvider.try_create(c);assert provider is not None
 original=record_value(s.to_record());stats=SearchStatistics();limits=SearchLimits(max_depth=p['depth'],max_nodes=p['nodes'],max_time_seconds=None,quiescence_max_depth=4,quiescence_hard_max_depth=8)
 qs=stamp();qt=time.perf_counter();cpu=time.process_time();ev=base if mode=='OFF' else ExactStaticMemo(c,base,capacity=p['capacity'],shadow=mode=='SHADOW');token=Cancel(qt+p['call_seconds'])
 res=S.run_root_search(s.state,c,ev,TranspositionTable(),limits,token,stats,use_tt=True,use_ordering=True,tuning=SearchTuning(),_history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
 end=stamp();r=dict(slot=slot,id=row['id'],family=row['family'],mode=mode,result=record_value(res),stats=record_value(stats),wall_seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-cpu,started_at=qs,ended_at=end,caller_deadline=token.flag,memo=None if mode=='OFF' else dict(ev.metrics),scope='Productionrun_root_search interface+memo eligibility/startup;compile/profile/provider setupoutside call,not fullAlphaBetaPlayerconstructioncost')
 write_record(out/f'query-{slot:03d}.json',r);record_interval(qs,end,'research',str(out/f'query-{slot:03d}.json'),out)
 v=stamp();assert record_value(s.to_record())==original;assert stats.runtime_pushes==stats.runtime_pops;assert stats.native_legality_fallbacks==stats.native_legality_operational_failures==0
 if res[0] is not None:assert res[0] in s.legal_actions()
 check=type(s).replay(c,s.to_record())
 for a in res[2]:check.submit(a)
 if mode!='OFF':assert ev.entries<=p['capacity'] and ev.metrics['peak_entries']<=p['capacity']
 r['Core_undo_action_PV']=True;record_interval(v,stamp(),'validation',f'staticmemo slot{slot} Core root/action/PV/undo/cap',out)
 return r


def parity(group):
 return len({json.dumps([x['result'],signature(x['stats'])],sort_keys=True) for x in group})==1 and all(not x['caller_deadline'] and x['result'][-1] not in ('cancelled','time_limit') for x in group)


def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 for f,h in p['sources'].items():assert sha(f)==h
 census=json.loads(gzip.decompress(Path(p['census_input']).read_bytes()))['rows'][p['census_index']];cost=json.loads(gzip.decompress(Path(p['cost_input']).read_bytes()))['rows'];assert [x['id'] for x in cost]==p['cost_ids']
 tick=time.perf_counter();begin=stamp();rows=[];groups=[];status='FAILED';halt=None
 try:
  census_rows=[]
  for mode in ('OFF','SHADOW','OFF'):
   if stopped() or time.perf_counter()-tick+p['call_seconds']>=p['batch_seconds']:raise RuntimeError('frozenbatch_or_stop')
   r=call(census,mode,len(rows),p,out);rows.append(r);census_rows.append(r);write_record(out/'queries.json',rows)
  m=census_rows[1]['memo'];rate=m['hits']/m['requests'] if m['requests'] else 0;overhead=census_rows[1]['wall_seconds']/((census_rows[0]['wall_seconds']+census_rows[2]['wall_seconds'])/2);ok=parity(census_rows) and rate>=p['minimum_shadow_hit_rate'] and overhead<=p['max_shadow_overhead'] and m['bypasses']==0
  write_record(out/'census-assessment.json',dict(parity=parity(census_rows),hit_rate=rate,shadow_overhead=overhead,all_shadow_hits_raw_value_checked=True,eligible=ok,scope='One engaged exposeddevelopment root only,no classgeneralization'))
  if not ok:status='NO_GO_CENSUS';halt='frozen shadowgate';return
  for row in cost:
   g=[]
   for mode in ('OFF','ON','ON','OFF'):
    if stopped() or time.perf_counter()-tick+p['call_seconds']>=p['batch_seconds']:halt='frozenbatch_or_stop';break
    r=call(row,mode,len(rows),p,out);rows.append(r);g.append(r);write_record(out/'queries.json',rows)
   if len(g)!=4:break
   same=parity(g);off=[x for x in g if x['mode']=='OFF'];on=[x for x in g if x['mode']=='ON'];c0=sum(x['cpu_seconds'] for x in off)
   groups.append(dict(id=row['id'],family=row['family'],parity=same,wall_OFF=sum(x['wall_seconds'] for x in off),wall_ON=sum(x['wall_seconds'] for x in on),cpu_OFF=c0,cpu_ON=sum(x['cpu_seconds'] for x in on),cpu_resolution_known=c0>0,memo=[x['memo'] for x in on]));write_record(out/'groups.json',groups)
   if not same:halt='work_or_value_or_deadline_mismatch';break
  eligible=len(groups)==len(cost) and all(x['parity'] and x['cpu_resolution_known'] for x in groups);wall=sum(x['wall_ON'] for x in groups)/sum(x['wall_OFF'] for x in groups) if groups else None;cpu=sum(x['cpu_ON'] for x in groups)/sum(x['cpu_OFF'] for x in groups) if groups and sum(x['cpu_OFF'] for x in groups)>0 else None
  by={}
  for x in groups:
   a=by.setdefault(str(x['family']),[0.,0.]);a[0]+=x['cpu_ON'];a[1]+=x['cpu_OFF']
  faster=sum(a<b for a,b in by.values());status='GO_SCOPED_COST' if eligible and wall<p['max_cost_ratio'] and cpu<p['max_cost_ratio'] and faster>=p['minimum_faster_families'] else 'NO_GO_OR_INCONCLUSIVE_COST'
  write_record(out/'cost-assessment.json',dict(eligible=eligible,groups=len(groups),wall_ratio=wall,cpu_ratio=cpu,faster_families=faster,family_cpu=by,status=status,limits='Knownfixedworkdevelopmenthistories only,all missing/cancelledslotsretained. WholeRootentrycost not wholePlayerconstruction/crossrule strength;defaultOFF.'))
 finally:
  r=dict(status=status,halt=halt,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,attempted=len(rows),maximum_calls=3+len(cost)*4,unconsumed=3+len(cost)*4-len(rows),new_Player_calls=0,new_games=0,new_builds=0,default_changed=False);write_record(out/'summary.json',r);print(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
