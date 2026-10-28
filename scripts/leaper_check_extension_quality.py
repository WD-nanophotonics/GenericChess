"""Frozen new-family equal-outer-time one-check-extension comparison; no product/default changes."""
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
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def orbit(a,b):return sorted({(sx*x,sy*y) for x,y in ((a,b),(b,a)) for sx in (-1,1) for sy in (-1,1)}-{(0,0)})
def union(*xs):return sorted(set().union(*(set(x) for x in xs)))
def prepare(out):
 assert not out.exists();out.mkdir(parents=True)
 oldpath=Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz')
 base=json.loads(gzip.decompress(oldpath.read_bytes()))['rows'][0]['RuleSet']
 w=orbit(1,0);f=orbit(1,1);n=orbit(2,1);c=orbit(3,1);z=orbit(3,2)
 triples=[(union(z,w),union(c,f),orbit(2,0)),(union(z,f),orbit(4,1),union(n,w)),(z,union(orbit(3,3),w),union(n,orbit(2,2))),(union(z,n),union(orbit(4,0),f),c),(union(z,orbit(2,2)),union(c,w),f),(union(z,orbit(3,0)),union(orbit(4,2),n),union(w,f))]
 homes=[[('K',0,0),('A',1,0),('A',2,0),('A',0,1),('B',3,0),('B',4,0),('B',1,1),('C',2,1),('C',3,1)],[('K',0,0),('A',1,0),('A',2,0),('A',0,1),('B',3,0),('B',4,0),('B',1,2),('C',2,1),('C',3,2)],[('K',0,0),('A',1,0),('A',2,0),('A',2,1),('B',3,0),('B',5,0),('B',1,1),('C',3,1),('C',4,1)],[('K',0,0),('A',2,0),('A',3,0),('A',1,1),('B',1,0),('B',4,0),('B',0,1),('C',2,1),('C',4,1)]]
 # Commit literal metadata BEFORE any Core/compiler/provider query.
 write_record(out/'metadata-before-Core.json',dict(board_size=7,triples=triples,homes=homes,max_ply=96,repetition_limit=4,selection='ALL six literal triples/four homes fixed; no seed/outcome filtering or replacement',source_base_sha256=sha(oldpath)))
 rows=[]
 for family,triple in enumerate(triples):
  for layout,home in enumerate(homes):
   r=copy.deepcopy(base);r.update(board_size=7,max_ply=96,initial_position=[[None]*7 for _ in range(7)],metadata={})
   r['piece_types']=[dict(type_id=typ,name=typ,movement_atoms=[dict(kind='leap',offset=list(o)) for o in offsets],is_anchor=typ=='K',is_promotable=False,promotion_target_ids=[]) for typ,offsets in zip(('K','A','B','C'),(union(w,f),*triple))]
   r['drop_allowed']={typ:[[False]*49,[False]*49] for typ in ('A','B','C')}
   for owner in (0,1):
    for typ,x,y in home:
     if owner:x,y=6-x,6-y
     assert r['initial_position'][y][x] is None
     r['initial_position'][y][x]=dict(owner=owner,base_type_id=typ,current_type_id=typ,promoted=False)
   fp=compute_fingerprint(ruleset_from_dict(r))
   rows.append(dict(id=f'ce7-f{family}-h{layout}',family=family,layout=layout,RuleSet=r,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),prefix_length=0,exposure='Prospectively frozen new DEVELOPMENT evaluation family; primitive leaps exposed; no claim random population holdout'))
 assert len({r['fingerprint'] for r in rows})==24
 write_record(out/'inputs.json',dict(schema=1,rows=rows));print(json.dumps(dict(inputs=24,families=6,input_sha256=sha(out/'inputs.json'))),flush=True)

def record_interval(begin,end,activity,evidence,out):
 if begin==end:
  p=out/'unverified-clock-intervals.json';d=read_json(p);d.setdefault('intervals',[]).append(dict(started_at=begin,ended_at=end,activity=activity,evidence=evidence,credited_seconds=0));write_json(p,d);return
 session.record_work(begin,end,activity,evidence)

def admission(plan,tick,batch,budget):
 for name in ('rollout.json','advisor.json','slack.json'):
  flags=read_json(Path('.local_agent')/name)
  if any(flags.get(k,False) for k in ('user_paused','stopped','research_stopped','stop_requested')):return 'scoped_stop'
 reserve=max(plan['inflight_reserve_seconds'],budget+1)
 if time.perf_counter()-tick+reserve>=batch:return 'batch_dispatch_reserve'
 if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<=plan['delivery_reserve_seconds']+reserve:return 'whole_delivery_reserve'
 return None

def choose(c,s,players,seat,on,budget,qid,out,depth):
 begin=stamp();t=time.perf_counter();cpu=time.process_time();token=CallerDeadline(t+budget)
 try:
  if seat not in players:players[seat]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_one_check_extension=on),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
  player=players[seat];assert player._tuning.use_one_check_extension==on and not player._tuning.use_pvs
  before=s.to_record();before_hash=digest(before);metrics=provider_metrics(player);packing=time.perf_counter()-t;remaining=budget-packing
  assert remaining>0,'construction/packing exhausted service allocation'
  limits=SearchLimits(max_depth=depth,max_nodes=500000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8)
  d=player.choose_action(s,limits,cancel_token=token);end=stamp();wall=time.perf_counter()-t
  q=dict(actual_tuning=record_value(player._tuning),evaluation_profile=record_value(player.evaluation_profile),query_id=qid,status='RETURNED',started_at=begin,ended_at=end,on=on,seat=seat,ply_before=s.state.ply_count,requested_service_seconds=budget,construction_packing_seconds=packing,limits=record_value(limits),service_wall_seconds=wall,cpu_seconds=time.process_time()-cpu,caller_deadline_observed=token.observed,record_before_sha256=before_hash,decision=record_value(d),provider_present=metrics['present'],provider_delta=metric_delta(metrics,provider_metrics(player)),timing_eligible=wall<=budget*1.1)
  write_record(out/'returns'/f'{qid}.json',q);record_interval(begin,end,'research',str(out/'returns'/f'{qid}.json'),out)
 except BaseException as e:
  write_record(out/f'failure-{qid}.json',dict(at=stamp(),error_type=type(e).__name__,error=str(e),wall=time.perf_counter()-t));raise
 v=stamp();assert s.to_record()==before and d.runtime_depth_balanced
 assert d.action is not None and d.action in s.legal_actions()
 assert metrics['present'] and d.native_legality_fallbacks==d.native_legality_operational_failures==0
 assert q['provider_delta']['availability'].get('declines',0)==0
 assert d.main_extension_max_path<=1
 pv=type(s).replay(c,before)
 for a in d.principal_variation:pv.submit(a)
 s.submit(d.action);q.update(record_after_sha256=digest(s.to_record()),pv_legal=True,root_unchanged=True)
 record_interval(v,stamp(),'validation',qid+':fullroot/action/PV/transition',out)
 return q

def accept_qualification(q,compiled,root):
 d=q['decision']
 if d['completed_depth']==2:return 'completed_D2'
 # Existing search.py contract returns a complete root terminal proof before
 # iteration1. Validate it through full Core, never infer truth from score alone.
 from generic_chess.ai.evaluation.config import MATE_SCORE
 from scripts.verify_leaper_pvs_quality_pilot import action
 assert d['completed_depth']==0 and d.get('result_source')=='root_immediate_win' and d['score']==MATE_SCORE-1, 'qualification is neither completeD2 nor root terminal proof'
 c,probe=make_session(root);actor=probe.state.position.side_to_move
 probe.submit(action(d['action'],probe));assert probe.state.terminal_status.is_terminal and probe.state.terminal_status.winner==actor, 'claimed rootwin lacks actual full-Core terminal witness'
 return 'Core_verified_immediate_WIN'

def run(prepared,plan_path,out):
 assert not out.exists();plan=read_json(plan_path);assert sha(prepared/'inputs.json')==plan['input_sha256']
 for p,h in plan['sources'].items():assert sha(p)==h,p
 out.mkdir(parents=True);(out/'returns').mkdir();rows=read_json(prepared/'inputs.json')['rows'];assert len(rows)==24 and [r['id'] for r in rows]==plan['root_ids']
 write_record(out/'frozen.json',dict(plan=plan,input_sha256=sha(prepared/'inputs.json'),sources={p:Path(p).read_bytes().decode('utf8') for p in plan['sources']}))
 import generic_chess.native as native
 module=native._module();bp=Path(module.__file__);write_record(out/'loaded-binary.json',dict(module=bp.name,sha256=sha(bp),bytes=bp.stat().st_size,python=sys.version,platform=sys.platform))
 started=stamp();tick=time.perf_counter();halt=None;qual=[];qid=0
 prior=Path(plan['qualification_continuation_from']) if plan.get('qualification_continuation_from') else None
 oldqual=json.loads((prior/'qualification.json').read_bytes()) if prior else []
 if prior:
  assert len(oldqual)==24 and sum(x['status']=='NOT_RUN' for x in oldqual)==5
  write_record(out/'original-registration-failed.json',dict(original_gate='FAILEDslot18D2contract',amended_semantic_gate=True,original_qualification=oldqual,no_prior_query_repeated=True,no_deadline_extension=True))
 for ri,r in enumerate(rows):
  scores=[]
  for on in ((False,True) if ri%2==0 else (True,False)):
   x=dict(slot=len(qual),case_id=r['id'],on=on,status='NOT_RUN');halt=halt or admission(plan,tick,plan['qualification_seconds'],3)
   if not halt:
    try:
     c,s=make_session(r)
     reused=bool(prior and x['slot']<19)
     if reused:
      old=oldqual[x['slot']];assert old['case_id']==r['id'] and old['on']==on
      name=old['query_id']+'.json';raw=(prior/'returns'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==plan['prior_return_hashes'][name]
      (out/'returns'/name).write_bytes(raw);q=json.loads(raw);qid+=1
     else:
      q=choose(c,s,{},s.state.position.side_to_move,on,3,f'q{qid:04d}',out,2);qid+=1
     x.update(status='RETURNED_REUSED' if reused else 'RETURNED',query_id=q['query_id'],decision=q['decision'],original_status=oldqual[x['slot']]['status'] if prior else None)
     accepted=accept_qualification(q,c,r)
     assert accepted,'qualification must complete D2'
     x['accepted_goal']=accepted
     scores.append(q['decision']['score'])
    except Exception as e:x.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='qualification_failure'
   else:x['reason']=halt
   qual.append(x);write_record(out/'qualification.json',qual)
  # This mechanism deliberately changes the search tree; equal D2 scores are NOT required.
 # Action differences only qualify exposure, NEVER useful/true WDL.
 active={rows[i//2]['family'] for i,x in enumerate(qual) if x.get('on') and x.get('decision',{}).get('main_check_extensions',0)>0}
 differing=set()
 for i in range(0,len(qual),2):
  pair=qual[i:i+2]
  if len(pair)==2 and all('decision' in x for x in pair) and pair[0]['decision']['action']!=pair[1]['decision']['action']:differing.add(rows[i//2]['family'])
 write_record(out/'mechanism-exposure.json',dict(extended_families=sorted(active),action_difference_families=sorted(differing),limits='Exposure only,not corrected WDL/benefit; no root replacement'))
 if len(active)<3 or len(differing)<3:halt=halt or 'fewer_than3families_exposed_decision_difference'
 qualification_end=stamp();games=[];gtick=time.perf_counter()
 for ri,r in enumerate(rows):
  for on_seat in ((0,1) if ri%2==0 else (1,0)):
   g=dict(game_id=len(games),case_id=r['id'],family=r['family'],layout=r['layout'],fingerprint=r['fingerprint'],on_seat=on_seat,initial_record=r['record'],status='NOT_STARTED',queries=[])
   halt=halt or admission(plan,gtick,plan['game_batch_seconds'],1)
   if not halt:
    t=time.perf_counter();v=stamp()
    try:
     c,s=make_session(r);players={};record_interval(v,stamp(),'validation',r['id']+':fixedfullrules/replay',out);g.update(status='RUNNING',started_at=stamp(),setup_seconds=time.perf_counter()-t)
     while not s.state.terminal_status.is_terminal:
      halt=admission(plan,gtick,plan['game_batch_seconds'],1)
      if halt:break
      assert len(g['queries'])<96,'caller96turn cap before Core terminal'
      seat=s.state.position.side_to_move;q=choose(c,s,players,seat,seat==on_seat,1,f'g{qid:04d}',out,64);qid+=1;g['queries'].append(q)
      write_record(out/f'game-{g["game_id"]:02d}-queries.json',g['queries']);write_json(out/'progress.json',dict(at=stamp(),completed_games=len(games),active_game=g['game_id'],family=r['family'],turns=len(g['queries']),returns=qid,seconds=time.perf_counter()-gtick,effective_seconds=session.status()['effective_seconds']))
     g.update(status='TERMINAL' if s.state.terminal_status.is_terminal else 'UNFINISHED',final_record=record_value(s.to_record()),Core_terminal=record_value(s.state.terminal_status),Session_result=record_value(s.result),ended_at=stamp(),outer_seconds=time.perf_counter()-t,timing_eligible=all(q['timing_eligible'] for q in g['queries']))
    except Exception as e:g.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='game_or_validation_failure'
   g['reason']=halt;games.append(g);write_record(out/f'game-{g["game_id"]:02d}.json',g);write_record(out/'games.json',games);print(json.dumps({k:g[k] for k in ['game_id','family','layout','status','reason']}),flush=True)
 summary=dict(original_registered_gate='FAILED' if prior else 'as_recorded',qualification_amendment=bool(prior),reused_prior_returns=19 if prior else 0,started_at=started,qualification_ended_at=qualification_end,ended_at=stamp(),qualification_statuses=dict(Counter(x['status'] for x in qual)),game_statuses=dict(Counter(g['status'] for g in games)),planned_games=48,returns=qid,game_batch_seconds=time.perf_counter()-gtick,halt=halt,new_solver=0,new_build=0,product_changes=1,default_enabled=False,candidate="one-main-check-extension/v1")
 write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.mode=='prepare':prepare(a.prepared)
 else:run(a.prepared,a.plan,a.output)
