"""Single-span runtime-push wall observer; matched original before/after controls."""
from __future__ import annotations
import gzip,json,time,hashlib
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts.leaper_cost_profile_trial import signature,stamp,stopped
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from tools.local_agent.session import record_work

ROOT=Path('.local_agent/patrol-20261026-1051')
SOURCE=Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz')
@contextmanager
def observe_push(enabled):
 original=SearchPathRuntime._push_impl
 metrics={'calls':0,'seconds':0.0,'nested_calls':0,'exceptions':0,'active':0}
 def observed(self,*args,**kwargs):
  start=time.perf_counter();metrics['active']+=1
  metrics['nested_calls']+=int(metrics['active']>1)
  try:return original(self,*args,**kwargs)
  except BaseException:
   metrics['exceptions']+=1;raise
  finally:
   elapsed=time.perf_counter()-start
   if metrics['active']==1:metrics['seconds']+=elapsed
   metrics['active']-=1;metrics['calls']+=1
 try:
  if enabled:SearchPathRuntime._push_impl=observed
  yield metrics
 finally:SearchPathRuntime._push_impl=original

def run():
 plan=json.loads((ROOT/'push-span-plan-v2.json').read_bytes())
 out=ROOT/'push-span';assert not out.exists();out.mkdir()
 allrows=json.loads(gzip.decompress(SOURCE.read_bytes()))['rows']
 rows=[r for r in allrows if r['id'] in plan['case_ids']]
 assert [r['id'] for r in rows]==plan['case_ids']
 write_record(out/'source.json',{'driver':Path(__file__).read_bytes().decode('utf-8'),'input_original_sha256':hashlib.sha256(gzip.decompress(SOURCE.read_bytes())).hexdigest(),'plan':plan})
 tick=time.perf_counter();results=[];halt=None
 for row in rows:
  group=[]
  for arm in ('before','push_span','after'):
   slot=len(results);r={'slot':slot,'case_id':row['id'],'depth':8,'arm':arm,'fingerprint':row['fingerprint']}
   if halt or stopped() or time.perf_counter()-tick>=plan['batch_seconds']:
    r.update(status='NOT_RUN',reason=halt or 'stop_or_batch_cap');results.append(r);continue
   t=time.perf_counter();cpu=time.process_time();utc=stamp()
   try:
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']))
    s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));before=s.to_record()
    player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
    setup=time.perf_counter()-t
    limits=SearchLimits(max_depth=8,max_nodes=2000000,max_time_seconds=90,quiescence_max_depth=4,quiescence_hard_max_depth=8)
    with observe_push(arm=='push_span') as metrics:
     tcall=time.perf_counter();ccpu=time.process_time()
     decision=player.choose_action(s,limits)
     callseconds=time.perf_counter()-tcall;callcpu=time.process_time()-ccpu
    end=stamp();raw=record_value(decision)
    r.update(status='RETURNED',decision=raw,started_at=utc,ended_at=end,outer_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-cpu,setup_constructor_seconds=setup,choose_seconds=callseconds,choose_cpu_seconds=callcpu,observed_push=dict(metrics))
    write_record(out/f'return-{slot:03}.json',r);record_work(utc,end,'research',str(out/f'return-{slot:03}.json'))
    assert s.to_record()==before
    if decision.action is not None:assert decision.action in s.legal_actions()
    pv=GameSession.replay(c,before)
    for action in decision.principal_variation:pv.submit(action)
    if arm=='push_span':
     assert metrics['active']==0 and metrics['nested_calls']==0
     assert metrics['calls']-metrics['exceptions']==decision.runtime_pushes
     assert 0<=metrics['seconds']<=callseconds
    r.update(root_unchanged=True,pv_legal=True)
   except Exception as e:
    r.update(status='FAILED',error_type=type(e).__name__,error=str(e),ended_at=stamp());halt='execution_or_evidence_failure'
   group.append(r);results.append(r);write_record(out/'queries.json',results)
   write_record(out/'progress.json',{'slots':len(results),'case_id':row['id'],'arm':arm,'seconds':time.perf_counter()-tick,'halt':halt})
  if len(group)==3 and all(r['status']=='RETURNED' for r in group):
   complete=all(r['decision']['completed_depth']==8 for r in group)
   parity=signature(group[0]['decision'])==signature(group[1]['decision'])==signature(group[2]['decision'])
   write_record(out/f'group-{row["id"]}.json',{'complete':complete,'exact_nontiming_decision_parity':parity,'slots':[r['slot'] for r in group]})
   if complete and not parity:halt='complete_work_or_result_mismatch'
 write_record(out/'queries.json',results)
 write_record(out/'summary.json',{'seconds':time.perf_counter()-tick,'ended_at':stamp(),'halt':halt,'slots':len(results),'attempts':sum(r['status']!='NOT_RUN' for r in results),'counts':{s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})},'games':0,'solver':0,'product_changes':False})
 print((out/'summary.json').read_text(encoding='utf-8'))
if __name__=='__main__':run()
