"""Finite changed-density pure-Leaper resource calibration; no default changes."""
from __future__ import annotations
import argparse,copy,gzip,hashlib,json,sys,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from scripts.leaper_pvs_quality_pilot import make_session,digest,CallerDeadline,provider_metrics,metric_delta
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json,write_json
from tools.local_agent.session import record_work as _record_work

def record_work(begin,end,activity,evidence):
 if begin==end:
  # Preserve sub-resolution interval as uncredited, never fabricate endpoints.
  return dict(uncredited=True,reason="equal_UTC_endpoints",started_at=begin,ended_at=end,evidence=evidence)
 return _record_work(begin,end,activity,evidence)

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mask(a,b):return sorted({(sx*x,sy*y) for x,y in ((a,b),(b,a)) for sx in (-1,1) for sy in (-1,1)}-{(0,0)})
def inputs():
 old=json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet']
 orth=mask(1,0);diag=mask(1,1);king=sorted(set(orth+diag));knight=mask(2,1);camel=mask(3,1)
 triples=[(knight,orth,diag),(knight,diag,orth),(camel,orth,king),(mask(3,2),king,knight),(mask(2,2),mask(2,0),king),(sorted(set(knight+orth)),diag,camel)]
 rows=[]
 for f,(a,b,c) in enumerate(triples):
  r=copy.deepcopy(old);r.update(max_ply=128,initial_position=[[None]*5 for _ in range(5)])
  r['piece_types']=[]
  for typ,offsets in zip(('K','A','B','C'),(king,a,b,c)):
   r['piece_types'].append(dict(type_id=typ,name=typ,movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets],is_anchor=typ=='K',is_promotable=False,promotion_target_ids=[]))
  r['drop_allowed']={t:[[False]*25,[False]*25] for t in ('A','B','C')}
  for owner in (0,1):
   for typ,x,y in [('K',0,0),('A',1,0),('A',0,1),('B',2,0),('B',1,1),('C',2,1)]:
    if owner:x,y=4-x,4-y
    assert r['initial_position'][y][x] is None
    r['initial_position'][y][x]=dict(owner=owner,base_type_id=typ,current_type_id=typ,promoted=False)
  fingerprint=compute_fingerprint(ruleset_from_dict(r))
  rows.append(dict(id=f'dense5-f{f}-h0',family=f,fingerprint=fingerprint,RuleSet=r,record=dict(schema_version=1,ruleset_fingerprint=fingerprint,actions=[],resigned_by=None),exposure='New prospective development rule; later never heldout',prefix_length=0))
 return dict(schema=1,rows=rows,selection='Six literal mask triples and fixed symmetric12piece homes;no outcome-driven replacement',old_source_sha256=sha('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz'))
def prepare(output):
 assert not output.exists();output.mkdir(parents=True)
 value=inputs();write_record(output/'inputs.json',value)
 begin=stamp();checks=[]
 for row in value['rows']:
  c,s=make_session(row)
  checks.append(dict(case=row['id'],fingerprint=row['fingerprint'],complete_record=record_value(s.to_record()),legal_actions=len(s.legal_actions()),Core_terminal=record_value(s.state.terminal_status)))
 write_record(output/'preflight.json',checks)
 record_work(begin,stamp(),'validation',str(output/'preflight.json'))
 print(json.dumps(checks))
def load_prior(plan):
 prior=plan.get('continue_unstarted_from')
 if not prior:return None
 p=Path(prior);g=json.loads((p/'games.json').read_text(encoding='utf8'))
 assert len(g)==12 and g[0]['status']=='FAILED'
 assert g[0].get('error_type')=='LocalFlowError' and 'work must be within' in g[0].get('error','')
 assert all(x['status']=='NOT_STARTED' and not x['queries'] for x in g[1:])
 assert len(list((p/'returns').glob('g*.json')))==3
 return p

def admission(plan,tick,budget):
 r=read_json(Path('.local_agent/rollout.json'))
 if any(r.get(k,False) for k in ('stopped','user_paused','research_stopped','stop_requested')):return 'scoped_stop'
 if time.perf_counter()-tick+budget+3>=plan['batch_seconds']:return 'batch_dispatch_reserve'
 if plan.get('original_batch_deadline_utc') and (datetime.fromisoformat(plan['original_batch_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<=budget+3:return 'original_batch_deadline_reserve'
 if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<plan['delivery_reserve_seconds']+budget+3:return 'whole_run_delivery_reserve'
 return None

def choose(c,s,players,seat,budget,qid,out):
 # The deadline starts before construction/record packing. First turn pays its
 # seat's Player construction; compile/replay shared setup is reported separately.
 begin=stamp();t0=time.perf_counter();cpu=time.process_time();token=CallerDeadline(t0+budget)
 try:
  if seat not in players:
   players[seat]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
  p=players[seat];before=s.to_record();before_hash=digest(before);metrics=provider_metrics(p)
  packing=time.perf_counter()-t0;remaining=budget-packing
  assert remaining>0,'construction/packing exhausted allocated service budget'
  limits=SearchLimits(max_depth=64,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8)
  d=p.choose_action(s,limits,cancel_token=token)
  end=stamp();wall=time.perf_counter()-t0;cpu=time.process_time()-cpu
  q=dict(query_id=qid,status='RETURNED',started_at=begin,ended_at=end,requested_service_seconds=budget,construction_packing_seconds=packing,actual_limits=record_value(limits),service_wall_seconds=wall,cpu_seconds=cpu,caller_deadline_observed=token.observed,record_before_sha256=before_hash,decision=record_value(d),provider_present=metrics['present'],provider_delta=metric_delta(metrics,provider_metrics(p)),timing_eligible=wall<=budget*1.1)
  write_record(out/'returns'/f'{qid}.json',q)
  record_work(begin,end,'research',str(out/'returns'/f'{qid}.json'))
 except BaseException as e:
  end=stamp();write_record(out/f'failure-{qid}.json',dict(started_at=begin,ended_at=end,error_type=type(e).__name__,error=str(e),wall=time.perf_counter()-t0));raise
 v0=stamp()
 assert s.to_record()==before
 assert d.action is not None and d.action in s.legal_actions()
 assert d.runtime_depth_balanced
 assert metrics['present'] and d.native_legality_fallbacks==0 and d.native_legality_operational_failures==0
 assert q['provider_delta']['availability'].get('declines',0)==0
 pv=type(s).replay(c,before)
 for a in d.principal_variation:pv.submit(a)
 s.submit(d.action)
 q.update(seat=seat,record_after_sha256=digest(s.to_record()),pv_legal=True,root_unchanged=True)
 record_work(v0,stamp(),'validation',f'{qid}:actual action/full PV and complete root validation')
 return q

def run(prepared,plan_path,out):
 assert not out.exists();plan=read_json(plan_path);assert sha(prepared/'inputs.json')==plan['input_sha256']
 for p,h in plan['sources'].items():assert sha(p)==h,p
 rows=read_json(prepared/'inputs.json')['rows'];assert len(rows)==6
 out.mkdir(parents=True);(out/'returns').mkdir()
 write_record(out/'executed-source.json',dict(driver=Path(__file__).read_bytes().decode('utf8'),sources=plan['sources'],plan_sha256=sha(plan_path),input_sha256=sha(prepared/'inputs.json')))
 binaries={str(Path(m.__file__)):sha(m.__file__) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(m.__file__).endswith('.pyd') and 'generic' in str(m.__file__).lower()}
 write_record(out/'loaded-binaries.json',binaries)
 tick=time.perf_counter();games=[];halt=None;started=stamp();qid=0
 prior=load_prior(plan)
 if prior:qid=max(int(p.stem[1:]) for p in (prior/'returns').glob('g*.json'))+1
 for ri,row in enumerate(rows):
  for long_seat in ((0,1) if ri%2==0 else (1,0)):
   g=dict(game_id=len(games),case_id=row['id'],family=row['family'],fingerprint=row['fingerprint'],initial_record=row['record'],long_seat=long_seat,status='NOT_STARTED',queries=[])
   if prior and g['game_id']==0:
    old=read_json(prior/'game-00.json');games.append(old);write_record(out/'game-00-preserved-failed.json',old);continue
   halt=halt or admission(plan,tick,2)
   if not halt:
    setup=time.perf_counter();v0=stamp()
    try:
     c,s=make_session(row);players={}
     g.update(setup_seconds=time.perf_counter()-setup,started_at=stamp(),status='RUNNING')
     record_work(v0,stamp(),'validation',f'{row["id"]}:compiled/replayed exact frozen rule and h0 record')
     while not s.state.terminal_status.is_terminal:
      seat=s.state.position.side_to_move;budget=plan['policies']['long' if seat==long_seat else 'short']
      halt=admission(plan,tick,budget)
      if halt:break
      assert len(g['queries'])<128,'caller turn cap before actual Core terminal'
      q=choose(c,s,players,seat,budget,f'g{qid:04d}',out);qid+=1
      q.update(policy='long' if seat==long_seat else 'short',ply_before=s.state.ply_count-1)
      g['queries'].append(q)
      write_record(out/f'game-{g["game_id"]:02d}-queries.json',g['queries'])
      write_json(out/'progress.json',dict(at=stamp(),completed_games=len(games),active_game=g['game_id'],family=row['family'],turns=len(g['queries']),returns=qid,seconds=time.perf_counter()-tick))
     g.update(status='TERMINAL' if s.state.terminal_status.is_terminal else 'UNFINISHED',final_record=record_value(s.to_record()),Core_terminal=record_value(s.state.terminal_status),Session_result=record_value(s.result),ended_at=stamp(),timing_eligible=all(q['timing_eligible'] for q in g['queries']))
    except Exception as e:
     g.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='query_setup_or_validation_failure'
   g['reason']=halt;games.append(g);write_record(out/f'game-{g["game_id"]:02d}.json',g);write_record(out/'games.json',games)
   print(json.dumps({k:g[k] for k in ('game_id','family','status','reason')}),flush=True)
 summary=dict(started_at=started,ended_at=stamp(),seconds=time.perf_counter()-tick,planned_games=12,statuses=dict(Counter(g['status'] for g in games)),returns=qid,halt=halt,new_solver=0,new_build=0,product_changes=0)
 write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='prepare':prepare(a.prepared)
 else:run(a.prepared,a.plan,a.output)
