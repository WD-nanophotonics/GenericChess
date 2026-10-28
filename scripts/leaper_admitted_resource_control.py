"""Conditional fresh-pool default-policy resource control, not feature evidence."""
from scripts.leaper_resource_resolution_control import *
def run(prepared,plan_path,out):
 assert not out.exists();plan=read_json(plan_path);assert sha(prepared/'inputs.json')==plan['input_sha256']
 for p,h in plan['sources'].items():assert sha(p)==h,p
 out.mkdir(parents=True);(out/'returns').mkdir();rows=read_json(prepared/'inputs.json')['rows'];assert len(rows)==8 and [r['id'] for r in rows]==plan['root_ids']
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
 summary=dict(original_registered_gate='FAILED' if prior else 'as_recorded',qualification_amendment=bool(prior),reused_prior_returns=19 if prior else 0,started_at=started,qualification_ended_at=qualification_end,ended_at=stamp(),qualification_statuses=dict(Counter(x['status'] for x in qual)),game_statuses=dict(Counter(g['status'] for g in games)),planned_games=16,returns=qid,game_batch_seconds=time.perf_counter()-gtick,halt=halt,new_solver=0,new_build=0,product_changes=1,default_enabled=False,candidate="same-default-policy/resource1s-vs2s",feature_experiment=False)
 write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prepared,a.plan,a.output)
