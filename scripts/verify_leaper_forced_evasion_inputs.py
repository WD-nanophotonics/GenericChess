"""Independent public-record replay of completed structural admission nodes.
No new Player/solver/backend campaign. Unpreserved partial tails stay UNKNOWN.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,time
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.semantic_executor import semantic_engine_for
from tools.local_agent import session

def stamp():return datetime.now(timezone.utc).isoformat()
def key(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def verify(base, output_directory=None, record_intervals=False):
 b=Path(base);rows=json.loads((b/'literal-before-Core.json').read_text())['rows'];out=Path(output_directory) if output_directory else b/'independent-admission-verification';out.mkdir(exist_ok=False);tick=time.perf_counter();reports=[];submits=prefixplies=parents=checks=0
 for seed,row in enumerate(rows):
  f=b/f'admission-seed-{seed:02}.json'
  if not f.exists():continue
  a=json.loads(f.read_text());begin=stamp();t=time.perf_counter();c,_=make_session(row);engine=semantic_engine_for(c);saved=local=0;rootcount=0;nodes=a['nodes']
  for ni,n in enumerate(nodes):
   if session.stopped() or time.perf_counter()-tick>=1200:raise RuntimeError('readerstop/timecap;not originaldatarefill')
   record=deserialize_game_record(json.dumps(n['record']));s=GameSession.replay(c,record);prefixplies+=len(n['record']['actions']);actors=s.state.position.side_to_move;legal=s.legal_actions();actual=[record_value(x) for x in sorted(legal,key=lambda x:json.dumps(record_value(x),sort_keys=True))]
   if actual!=[x['action'] for x in n['children']]:
    write_record(out/'failure-original.json',dict(seed=seed,node=ni,expected=n,actual_full_legal_actions=actual));raise AssertionError('frontier changed')
   assert len(legal)==n['legal_count'];mapping={key(record_value(x)):x for x in legal};wins=[];forced=[]
   for ci,expected in enumerate(n['children']):
    clone=GameSession.replay(c,record);prefixplies+=len(n['record']['actions']);clone.submit(mapping[key(expected['action'])]);submits+=1;local+=1;saved+=1
    result=record_value(clone.result);checked=False;count=None
    if clone.result.status.value=='ongoing':
     checked=engine.in_check(clone.state.position,clone.state.position.side_to_move)
     if checked:count=len(clone.legal_actions());checks+=1
    derived=dict(action=expected['action'],result=result,checked=checked,complete_evasion_count=count)
    if derived!=expected:
     write_record(out/'failure-original.json',dict(seed=seed,node=ni,child=ci,original=expected,actual=derived,record=record_value(clone.to_record())));raise AssertionError('child behavior changed')
    if clone.result.winner==actors:wins.append(expected['action'])
    if checked and count==1:forced.append(expected['action'])
   assert wins==n['immediate_win_actions'] and [x['action'] for x in n['forced_checking_actions']]==forced
   qualified=len(legal)>1 and not wins and bool(forced)
   assert not qualified,'producer overlooked qualified completeparent'
   parents+=1;rootcount+=1
  tail=a['direct_children']-saved;assert tail>=0 and (tail==0 or a['reason']=='directchildcap')
  end=stamp();r=dict(seed=seed,status='PASS_COMPLETE_SAVED_NODES',complete_parents=rootcount,explicit_child_submits=local,original_direct_children=a['direct_children'],unpreserved_original_partial_tail=tail,tail_interpretation='UNKNOWN;original midparent returns notsaved,never reconstructed as originals',started_at=begin,ended_at=end,seconds=time.perf_counter()-t);write_record(out/f'seed-{seed:02}.json',r);reports.append(r);
  if record_intervals:session.record_work(begin,end,'validation',str(out/f'seed-{seed:02}.json'))
  print(json.dumps(r),flush=True)
 result=dict(status='PASS_SAVED_ADMISSION_SCOPE',complete_parents=parents,explicit_child_submits=submits,literal_prefix_replay_plies=prefixplies,checked_children=checks,unpreserved_original_partial_tail=sum(r['unpreserved_original_partial_tail'] for r in reports),reported_original_direct_children=sum(r['original_direct_children'] for r in reports),seeds=len(reports),seconds=time.perf_counter()-tick,new_Player=0,new_solver=0,scope='Independent publicGameRecord replay,sharedCore implementation;not allCoretrialwork or classabsenceproof. Single-evasion candidate remainsSTOP/0fitness;partial tails UNKNOWN.')
 write_record(out/'summary.json',result);print(json.dumps(result));return result
if __name__=='__main__':
 import sys;verify(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
