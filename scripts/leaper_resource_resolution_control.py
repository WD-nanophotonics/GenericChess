"""Frozen new-family equal-outer-time default-controller resource-resolution control; no product/default changes."""
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
 budget=budget*(2 if on else 1)
 begin=stamp();t=time.perf_counter();cpu=time.process_time();token=CallerDeadline(t+budget)
 try:
  if seat not in players:players[seat]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
  player=players[seat];assert not player._tuning.use_one_check_extension and not player._tuning.use_pvs
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
 if d['completed_depth']==1:return 'completed_D1'
 # Existing search.py contract returns a complete root terminal proof before
 # iteration1. Validate it through full Core, never infer truth from score alone.
 from generic_chess.ai.evaluation.config import MATE_SCORE
 from scripts.verify_leaper_pvs_quality_pilot import action
 assert d['completed_depth']==0 and d.get('result_source')=='root_immediate_win' and d['score']==MATE_SCORE-1, 'qualification is neither completeD1 nor root terminal proof'
 c,probe=make_session(root);actor=probe.state.position.side_to_move
 probe.submit(action(d['action'],probe));assert probe.state.terminal_status.is_terminal and probe.state.terminal_status.winner==actor, 'claimed rootwin lacks actual full-Core terminal witness'
 return 'Core_verified_immediate_WIN'

def run(prepared,plan_path,out):
 assert not out.exists();plan=read_json(plan_path);assert sha(prepared/'inputs.json')==plan['input_sha256']
 for p,h in plan['sources'].items():assert sha(p)==h,p
 out.mkdir(parents=True);(out/'returns').mkdir();rows=read_json(prepared/'inputs.json')['rows'];assert len(rows)==12 and [r['id'] for r in rows]==plan['root_ids']
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
      q=choose(c,s,{},s.state.position.side_to_move,on,1,f'q{qid:04d}',out,64);qid+=1
     x.update(status='RETURNED_REUSED' if reused else 'RETURNED',query_id=q['query_id'],decision=q['decision'],original_status=oldqual[x['slot']]['status'] if prior else None)
     accepted='legal_current_service_return' if q['timing_eligible'] else None
     assert accepted,'qualification must complete D1'
     x['accepted_goal']=accepted
     scores.append(q['decision']['score'])
    except Exception as e:x.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='qualification_failure'
   else:x['reason']=halt
   qual.append(x);write_record(out/'qualification.json',qual)
  # This mechanism deliberately changes the search tree; equal D2 scores are NOT required.
 # This is a resource positive control, not a feature/gate amendment.
 # No nominal depth or initial action-difference eligibility surrogate.
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
      assert s.state.ply_count<r['RuleSet']['max_ply'],'actual frozen ruleclock before Core terminal'
      seat=s.state.position.side_to_move;q=choose(c,s,players,seat,seat==on_seat,1,f'g{qid:04d}',out,64);qid+=1;g['queries'].append(q)
      write_record(out/f'game-{g["game_id"]:02d}-queries.json',g['queries']);write_json(out/'progress.json',dict(at=stamp(),completed_games=len(games),active_game=g['game_id'],family=r['family'],turns=len(g['queries']),returns=qid,seconds=time.perf_counter()-gtick,effective_seconds=session.status()['effective_seconds']))
     g.update(status='TERMINAL' if s.state.terminal_status.is_terminal else 'UNFINISHED',final_record=record_value(s.to_record()),Core_terminal=record_value(s.state.terminal_status),Session_result=record_value(s.result),ended_at=stamp(),outer_seconds=time.perf_counter()-t,timing_eligible=all(q['timing_eligible'] for q in g['queries']))
    except Exception as e:g.update(status='FAILED',error_type=type(e).__name__,error=str(e));halt='game_or_validation_failure'
   g['reason']=halt;games.append(g);write_record(out/f'game-{g["game_id"]:02d}.json',g);write_record(out/'games.json',games);print(json.dumps({k:g[k] for k in ['game_id','family','layout','status','reason']}),flush=True)
 summary=dict(original_registered_gate='FAILED' if prior else 'as_recorded',qualification_amendment=bool(prior),reused_prior_returns=19 if prior else 0,started_at=started,qualification_ended_at=qualification_end,ended_at=stamp(),qualification_statuses=dict(Counter(x['status'] for x in qual)),game_statuses=dict(Counter(g['status'] for g in games)),planned_games=24,returns=qid,game_batch_seconds=time.perf_counter()-gtick,halt=halt,new_solver=0,new_build=0,product_changes=1,default_enabled=False,candidate="same-default-policy/resource1s-vs2s",feature_experiment=False)
 write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['run']);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 run(a.prepared,a.plan,a.output)
