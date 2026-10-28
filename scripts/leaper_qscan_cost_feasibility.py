"""Exclusive-cost feasibility of pure-Leaper Q inventory/count scans; no Player."""
import argparse,cProfile,gzip,json,pstats,time
from pathlib import Path
from scripts.leaper_quiet_root_intervention import S,SearchStatistics,SearchLimits,TranspositionTable,SearchTuning,EvaluationConfig,EvaluationProfileCache,Evaluator,make_session,record_value,write_record,sha,stamp,stopped,record_interval
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns

TIMES={'ordering_seconds','legal_generation_seconds','evaluation_seconds','root_scan_seconds','time_to_first_legal_action','time_to_first_completed_iteration','quiet_geometry_build_seconds'}
def signature(x):return {k:v for k,v in x.items() if k not in TIMES and not k.endswith('_seconds')}
class Cancel:
 def __init__(self,deadline):self.deadline=deadline;self.last=0;self.flag=False
 def is_cancelled(self):
  t=time.perf_counter()
  if t-self.last>.25:self.last=t;self.flag=stopped() or t>=self.deadline
  return self.flag

def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert sha(__file__)==p['source_sha256'];assert sha(p['input'])==p['input_sha256'];assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 data=json.loads(gzip.decompress(Path(p['input']).read_bytes()))['rows'];rows=json.loads(Path(p['prior_queries']).read_bytes()) if p.get('prior_queries') else [];groups=p.get('prior_groups',[]);begin=stamp();tick=time.perf_counter();status='FAILED';error=None
 try:
  for index in p['indices']:
   group=[];c,s=make_session(data[index]);assert _plain_leaper_hash_patterns(c) is not None;cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);ev=Evaluator(c,profile,cfg);root=record_value(s.to_record())
   for arm in ['before','profile','after']:
    if stopped() or time.perf_counter()-tick+p['call_seconds']>=p['batch_seconds']:raise RuntimeError('frozen_batch_or_stop')
    provider=NativeSemanticLegalityProvider.try_create(c);assert provider is not None
    stats=SearchStatistics();lim=SearchLimits(max_depth=p['depth'],max_nodes=p['nodes'],max_time_seconds=None,quiescence_max_depth=4,quiescence_hard_max_depth=8);prof=cProfile.Profile(timer=time.process_time) if arm=='profile' else None
    qs=stamp();qt=time.perf_counter();cpu=time.process_time();token=Cancel(qt+p['call_seconds'])
    if prof:prof.enable()
    try:res=S.run_root_search(s.state,c,ev,TranspositionTable(),lim,token,stats,use_tt=True,use_ordering=True,tuning=SearchTuning(),_history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check)
    finally:
     if prof:prof.disable()
    end=stamp();r=dict(index=index,id=data[index]['id'],arm=arm,result=record_value(res),stats=record_value(stats),started_at=qs,ended_at=end,wall_seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-cpu,caller_deadline=token.flag)
    write_record(out/f'query-{len(rows):02d}.json',r);record_interval(qs,end,'research',str(out/f'query-{len(rows):02d}.json'),out)
    assert record_value(s.to_record())==root;assert stats.native_legality_fallbacks==stats.native_legality_operational_failures==0;assert stats.runtime_pushes==stats.runtime_pops
    if res[0] is not None:assert res[0] in s.legal_actions()
    check=type(s).replay(c,s.to_record())
    for a in res[2]:check.submit(a)
    r['Core_PV_root_rollback']=True
    if prof:
     ps=pstats.Stats(prof);cost=[]
     for (file,line,name),(cc,nc,tt,ct,callers) in ps.stats.items():cost.append(dict(file=Path(file).name,line=line,name=name,calls=nc,exclusive_cpu=tt,inclusive_cpu=ct))
     write_record(out/f'profile-{index:02d}.json',dict(timer='process_time',total_exclusive_cpu=ps.total_tt,functions=sorted(cost,key=lambda x:-x['exclusive_cpu']),scope='InstrumentedCPUallocation,not uninstrumented savings estimate'))
     r['instrumented_total_cpu']=ps.total_tt;r['scan_cpu']=sum(x['exclusive_cpu'] for x in cost if x['file']=='quiescence.py' and x['name'] in ('enemy_board_count','material_inventory'));r['scan_calls']=sum(x['calls'] for x in cost if x['file']=='quiescence.py' and x['name'] in ('enemy_board_count','material_inventory'))
    rows.append(r);group.append(r);write_record(out/'queries.json',rows)
   parity=len({json.dumps([x['result'],signature(x['stats'])],sort_keys=True) for x in group})==1 and all(not x['caller_deadline'] for x in group)
   obs=group[1];groups.append(dict(index=index,parity=parity,instrumented_scan_fraction=obs['scan_cpu']/obs['instrumented_total_cpu'] if obs['instrumented_total_cpu']>0 else None,observer_wall_ratio=obs['wall_seconds']/((group[0]['wall_seconds']+group[2]['wall_seconds'])/2),scan_calls=obs['scan_calls']));write_record(out/'groups.json',groups)
   if not parity:break
  eligible=len(groups)==p.get('expected_groups',len(p['indices'])) and all(x['parity'] for x in groups);denom=sum(x.get('instrumented_total_cpu',0) for x in rows);fraction=sum(x.get('scan_cpu',0) for x in rows)/denom if denom>0 else None;overhead=max(x['observer_wall_ratio'] for x in groups)
  status='GO_ONE_PROTOTYPE' if eligible and fraction is not None and fraction>=p['minimum_instrumented_fraction'] and overhead<=p['max_observer_ratio'] else 'NO_GO_OR_INCONCLUSIVE'
  write_record(out/'assessment.json',dict(eligible=eligible,weighted_instrumented_scan_fraction=fraction,max_observer_wall_ratio=overhead,gate=status,limits='Known development families,Node-limited productionrootinterface,not independent quality/strength or wholePlayercost. No parent protocol changed. No new backend build. No new game.'))
 except Exception as e:error=type(e).__name__+':'+str(e);raise
 finally:
  r=dict(status=status,error=error,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,queries=len(rows),expected=len(p['indices'])*3,new_Player_calls=0,new_games=0,new_builds=0);write_record(out/'summary.json',r);print(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
