"""Cold Player-object lifecycle follow-up, keeping the earlier failed gate intact."""
import argparse,gzip,json,time
from pathlib import Path
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator
from scripts.leaper_qscan_cost_feasibility import Cancel
from scripts.leaper_quiet_root_intervention import SearchLimits,SearchTuning,make_session,record_value,write_record,sha,stamp,stopped,record_interval

def signature(d):return {k:v for k,v in d.items() if not k.endswith('_seconds') and k not in {'time_to_first_legal_action','time_to_first_completed_iteration'}}

def run(plan_path,out):
 p=json.loads(plan_path.read_bytes());assert not out.exists();out.mkdir();write_record(out/'frozen.json',p)
 for f,h in p['sources'].items():assert sha(f)==h
 data=json.loads(gzip.decompress(Path(p['input']).read_bytes()))['rows'];assert [x['id'] for x in data]==p['ids'];begin=stamp();tick=time.perf_counter();rows=[];groups=[];status='FAILED';halt=None;attempted=0;active_start=None;credited=False
 try:
  for source in data:
   c,s=make_session(source);before=s.to_record();g=[]
   for on in (False,True,True,False):
    if stopped() or time.perf_counter()-tick+p['call_seconds']>=p['batch_seconds']:halt='frozen_batch_or_stop';break
    qs=stamp();active_start=qs;credited=False;attempted+=1;qt=time.perf_counter();cpu=time.process_time();player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
    assert player.native_legality_provider is not None;binary=Path(player.native_legality_provider.native_rules.backend_module.__file__);assert sha(binary)==p['native_sha256'];assert not player.evaluation_profile_cache_hit
    if on:player._evaluator=PureLeaperMaskEvaluator(c,player._evaluator)
    setup=time.perf_counter()-qt;token=Cancel(qt+p['call_seconds']);d=player.choose_action(s,SearchLimits(max_depth=p['depth'],max_nodes=p['nodes'],max_time_seconds=None,quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
    end=stamp();r=dict(slot=len(rows),id=source['id'],family=source['family'],on=on,decision=record_value(d),started_at=qs,ended_at=end,wall_seconds=time.perf_counter()-qt,cpu_seconds=time.process_time()-cpu,constructor_seconds=setup,caller_deadline=token.flag,mask_metrics=dict(player._evaluator.metrics) if on else None,native_binary_name=binary.name,native_sha256=p['native_sha256'],scope='ColdPlayerobject+profile+Nativeprovider+masksetup+choose_action;existing compiledRuleSet/session and alreadyloaded process/binary excluded')
    write_record(out/f'query-{len(rows):02d}.json',r);record_interval(qs,end,'research',str(out/f'query-{len(rows):02d}.json'),out);credited=True
    v=stamp();assert s.to_record()==before and d.runtime_depth_balanced;assert d.native_legality_fallbacks==d.native_legality_operational_failures==0;assert d.action in s.legal_actions()
    check=type(s).replay(c,before)
    for a in d.principal_variation:check.submit(a)
    if on:assert player._evaluator.metrics['fallback_calls']==0
    record_interval(v,stamp(),'validation',f'coldPlayer slot{len(rows)} fullCoreundo/PV/Native/no-maskfallback',out);r['Core_verified']=True;rows.append(r);g.append(r);write_record(out/'queries.json',rows);active_start=None
   if len(g)!=4:break
   same=len({json.dumps(signature(x['decision']),sort_keys=True) for x in g})==1 and all(not x['caller_deadline'] for x in g);off=[x for x in g if not x['on']];on=[x for x in g if x['on']];c0=sum(x['cpu_seconds'] for x in off)
   groups.append(dict(id=source['id'],family=source['family'],parity=same,wall_OFF=sum(x['wall_seconds'] for x in off),wall_ON=sum(x['wall_seconds'] for x in on),cpu_OFF=c0,cpu_ON=sum(x['cpu_seconds'] for x in on),cpu_resolution_known=c0>0));write_record(out/'groups.json',groups)
   if not same:halt='work_value_or_deadline_mismatch';break
  eligible=len(groups)==len(data) and all(x['parity'] and x['cpu_resolution_known'] for x in groups);wall=sum(x['wall_ON'] for x in groups)/sum(x['wall_OFF'] for x in groups) if groups else None;den=sum(x['cpu_OFF'] for x in groups);cpu=sum(x['cpu_ON'] for x in groups)/den if den else None;families={}
  for x in groups:
   f=families.setdefault(str(x['family']),[0.,0.]);f[0]+=x['cpu_ON'];f[1]+=x['cpu_OFF']
  faster=sum(a<b for a,b in families.values());status='GO_SCOPED_COLD_LIFECYCLE' if eligible and wall<p['max_cost_ratio'] and cpu<p['max_cost_ratio'] and faster>=p['minimum_faster_families'] else 'NO_GO_OR_INCONCLUSIVE_LIFECYCLE'
  write_record(out/'assessment.json',dict(status=status,eligible=eligible,groups=len(groups),wall_ratio=wall,cpu_ratio=cpu,faster_families=faster,family_cpu=families,limits='Same exposeddevelopment roots,repeatedcostcontrols notnew independentstrength;earlierRootgate remainsINCONCLUSIVE;no games/default/boardclass expansion.'))
 except Exception as e:
  import traceback
  write_record(out/'failure.json',dict(at=stamp(),error=type(e).__name__+':'+str(e),traceback=traceback.format_exc(),attempted_objects=attempted,completed_rows=len(rows)))
  if active_start is not None and not credited:record_interval(active_start,stamp(),'research',str(out/'failure.json'),out)
  raise
 finally:
  r=dict(status=status,halt=halt,started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-tick,calls=len(rows),max_calls=len(data)*4,unconsumed=len(data)*4-len(rows),AlphaBetaPlayer_objects=attempted,new_games=0,new_builds=0,default_changed=False);write_record(out/'summary.json',r);print(r)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();run(x.plan,x.output)
