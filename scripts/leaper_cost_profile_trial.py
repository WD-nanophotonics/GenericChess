"""Fixed-work, overhead-controlled pure-Leaper cost attribution; no product edits."""
from __future__ import annotations
import cProfile,gzip,hashlib,json,pstats,time,sys
from pathlib import Path
from datetime import datetime,timezone
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from tools.local_agent.session import record_work
from tools.local_agent.common import read_json

ROOT=Path('.local_agent/patrol-20261026-1051')
SOURCE=Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz')
TIMES={'elapsed_seconds','time_to_first_legal_action','time_to_first_completed_iteration','ordering_seconds','legal_generation_seconds','evaluation_seconds'}
def stamp():return datetime.now(timezone.utc).isoformat()
def signature(d):return {k:v for k,v in d.items() if k not in TIMES}
def stopped():
 return read_json(Path('.local_agent/rollout.json')).get('user_paused',False) or read_json(Path('.local_agent/slack.json')).get('stopped',False)
def run():
 plan=json.loads((ROOT/'profile-plan.json').read_bytes())
 out=ROOT/'profile';assert not out.exists();out.mkdir()
 inputs=json.loads(gzip.decompress(SOURCE.read_bytes()))['rows']
 assert [x['id'] for x in inputs]==plan['case_ids']
 write_record(out/'source.json',{'driver':Path(__file__).read_bytes().decode('utf-8'),'input_original_sha256':hashlib.sha256(gzip.decompress(SOURCE.read_bytes())).hexdigest(),'plan':plan})
 started=time.perf_counter();results=[];halt=None
 for depth in plan['depths']:
  for row in inputs:
   group=[]
   for arm in ('before','profile','after'):
    slot=len(results);result={'slot':slot,'case_id':row['id'],'depth':depth,'arm':arm,'fingerprint':row['fingerprint']}
    if halt or stopped() or time.perf_counter()-started>=plan['batch_seconds']:
     result.update(status='NOT_RUN',reason=halt or 'stop_or_batch_cap');results.append(result);continue
    t0=time.perf_counter();cpu=time.process_time();utc=stamp();prof=None
    try:
     c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']))
     s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));before=s.to_record()
     player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
     setup=time.perf_counter()-t0
     limits=SearchLimits(max_depth=depth,max_nodes=plan['nodes'],max_time_seconds=plan['call_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8)
     call0=time.perf_counter();cpu0=time.process_time()
     if arm=='profile':
      prof=cProfile.Profile(timer=time.process_time);prof.enable()
     try: decision=player.choose_action(s,limits)
     finally:
      if prof:prof.disable()
     end=stamp();calltime=time.perf_counter()-call0;callcpu=time.process_time()-cpu0
     raw=record_value(decision)
     result.update(status='RETURNED',decision=raw,started_at=utc,ended_at=end,outer_seconds=time.perf_counter()-t0,cpu_seconds=time.process_time()-cpu,choose_seconds=calltime,choose_cpu_seconds=callcpu,setup_constructor_seconds=setup)
     write_record(out/f'return-{slot:03}.json',result)
     # Record only the actual evidenced compute interval, not subsequent I/O/idle.
     record_work(utc,end,'research',str(out/f'return-{slot:03}.json'))
     if prof:
      stats=pstats.Stats(prof);rows=[]
      for (file,line,name),(cc,nc,tt,ct,callers) in stats.stats.items():
       rows.append({'file':file,'line':line,'name':name,'primitive_calls':cc,'total_calls':nc,'exclusive_instrumented_cpu':tt,'inclusive_instrumented_cpu':ct,'callers':[{'file':k[0],'line':k[1],'name':k[2],'metrics':v} for k,v in callers.items()]})
      write_record(out/f'profile-{slot:03}.json',{'total_tt':stats.total_tt,'functions':rows,'timer':'time.process_time','limits':'instrumented CPU includes timer/observer disturbance; not uninstrumented wall or C region allocation'})
     assert s.to_record()==before,'root mutation'
     if decision.action is not None:assert decision.action in s.legal_actions()
     pv=GameSession.replay(c,before)
     for a in decision.principal_variation:pv.submit(a)
     result.update(root_unchanged=True,pv_legal=True)
    except Exception as e:
     result.update(status='FAILED',error_type=type(e).__name__,error=str(e),ended_at=stamp())
     halt='execution_or_evidence_failure'
    results.append(result);group.append(result);write_record(out/'queries.json',results)
    write_record(out/'progress.json',{'slots':len(results),'last_case':row['id'],'last_arm':arm,'depth':depth,'seconds':time.perf_counter()-started,'halt':halt})
   if len(group)==3 and all(x['status']=='RETURNED' for x in group):
    signatures=[signature(x['decision']) for x in group]
    complete=all(x['decision']['completed_depth']==depth for x in group)
    write_record(out/f'group-{depth}-{row["id"]}.json',{'complete':complete,'exact_nontiming_decision_parity':signatures[0]==signatures[1]==signatures[2],'slots':[x['slot'] for x in group]})
    if complete and not signatures[0]==signatures[1]==signatures[2]:halt='complete_work_or_result_mismatch'
  # A deeper phase is useful only after observer behavior is qualified.
  phase=[r for r in results if r['depth']==depth]
  groups=[json.loads(p.read_bytes()) for p in out.glob(f'group-{depth}-*.json')]
  if depth==plan['depths'][0] and (len(groups)!=len(inputs) or not all(g['complete'] and g['exact_nontiming_decision_parity'] for g in groups)):
   halt=halt or 'initial_observer_qualification_incomplete'
 write_record(out/'queries.json',results)
 write_record(out/'summary.json',{'ended_at':stamp(),'seconds':time.perf_counter()-started,'halt':halt,'attempts':sum(r['status']!='NOT_RUN' for r in results),'slots':len(results),'counts':{s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})},'games':0,'solver':0,'product_changes':False})
 print((out/'summary.json').read_text(encoding='utf-8'))
if __name__=='__main__':run()
