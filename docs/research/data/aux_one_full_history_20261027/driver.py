"""One frozen archived-history replay; no new Player, game or training."""
from __future__ import annotations
import json
from pathlib import Path
import sys
from hashlib import sha256
from time import perf_counter,process_time
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution,compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,NonScoringTerminal

def digest(value):
 return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def physical(s):
 p=s.state.position
 return p.board,p.hands,p.side_to_move,p.ruleset_fingerprint,p.aux_state,p.board_shape,s.state.ply_count,s.state.terminal_status,s.result

def main():
 plan_path=ROOT/'.local_agent/one-history-942bc7a8-plan.json'
 input_path=ROOT/'.local_agent/one-history-942bc7a8-input.json'
 plan=json.loads(plan_path.read_bytes());raw=input_path.read_bytes();x=json.loads(raw)
 assert sha256(raw).hexdigest()=='62541ed42c093b8ce420131f364ef40c863a80cd8b3058e6da5e85e66b24a2aa'
 began,cpu=perf_counter(),process_time()
 def guard():
  for n in ['rollout','advisor','slack']:
   f=json.loads((ROOT/'.local_agent'/(n+'.json')).read_bytes())
   if f.get('user_paused') or f.get('stopped'): raise RuntimeError('STOPPED_USER')
  if (datetime.now().astimezone()-datetime.fromisoformat(plan['origin'])).total_seconds()>=60*plan['whole_minutes']:
   raise RuntimeError('WHOLE_CHECK_CAP')
 out=ROOT/'docs/research/data/aux_one_full_history_20261027'
 out.mkdir(parents=True,exist_ok=False)
 (out/'input.json').write_bytes(raw);(out/'plan.json').write_bytes(plan_path.read_bytes())
 (out/'driver.py').write_bytes(Path(__file__).read_bytes())
 rule=ruleset_from_dict(x['rule'])
 assert compute_fingerprint(rule)==x['final_record']['ruleset_fingerprint']
 assert x['initial_record']['ruleset_fingerprint']==compute_fingerprint(rule)
 results=[];states={};failure=None
 try:
  products={}
  for name,compiler in [('legacy',compile_ruleset_for_execution),('semantic',compile_legacy_ruleset_for_semantic_execution)]:
   guard();t=perf_counter();products[name]=compiler(rule)
   results.append(dict(kind='compile',backend=name,type=type(products[name]).__name__,wall=perf_counter()-t))
  for phase in ['full','proper_prefix']:
   record=dict(x['final_record'])
   if phase=='proper_prefix':record['actions']=record['actions'][:-1]
   parsed=deserialize_game_record(json.dumps(record))
   for name,compiled in products.items():
    guard();t,c=perf_counter(),process_time();s=GameSession.replay(compiled,parsed);guard()
    try:label=FixedScaleSessionEnv(s,unit_type='A').terminal()
    except NonScoringTerminal:label=None
    counts=dict(s.state.repetition_counts);last=s.state.history[-1].position_key
    history=[dict(position_key=h.position_key,actor=h.actor,action_signature=h.action_signature,gave_check=h.gave_check) for h in s.state.history]
    row=dict(kind='replay',phase=phase,backend=name,actions=len(record['actions']),wall=perf_counter()-t,cpu=process_time()-c,Core_status=s.state.terminal_status.status.value,Core_winner=s.state.terminal_status.winner,Session_status=s.result.status.value,Session_winner=s.result.winner,learner_terminal_player0=label,ply=s.state.ply_count,history_entries=len(history),repetition_entries=len(counts),maximum_repetition_count=max(counts.values()),current_position_repetition_count=counts.get(last),history_sha256=digest(history),repetition_counts_sha256=digest(list(s.state.repetition_counts)),record_dataclass_equal=s.to_record()==parsed)
    results.append(row);states[phase,name]=s
  comparisons=[]
  for phase in ['full','proper_prefix']:
   a,b=states[phase,'legacy'],states[phase,'semantic']
   comparisons.append(dict(phase=phase,physical_equal=physical(a)==physical(b),record_equal=a.to_record()==b.to_record(),history_equal=a.state.history==b.state.history,repetition_counts_equal=a.state.repetition_counts==b.state.repetition_counts))
  assert all(r['physical_equal'] and r['record_equal'] for r in comparisons)
 except Exception as error:
  failure=dict(type=type(error).__name__,message=str(error));comparisons=[]
 result=dict(scope='Exactly one preselected original complete GameRecord and its one-move-shorter prefix; four current replays, no new play/search/training or other-slot analysis',input_sha256=sha256(raw).hexdigest(),driver_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),whole_wall=perf_counter()-began,whole_cpu=process_time()-cpu,stored_terminal=x['stored_terminal'],stored_status=x['stored_status'],stored_utility=x['stored_utility'],original_slot_status=x['original_slot']['original_status'],recovered_status=x['original_slot']['status'],results=results,comparisons=comparisons,failure=failure)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
