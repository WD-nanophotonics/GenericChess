import json,time,traceback
from pathlib import Path
from scripts.research_record import record_value,write_record
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
p=Path('.local_agent/pvs-20261022');inputs=json.loads((p/'staged-utility/inputs.json').read_text());assert not(p/'eval-repeat-results.json').exists();out={'rows':[],'failures':[]};start=time.perf_counter()
class Trace:
 def __init__(self,original):
  assert type(original) is Evaluator
  self.original=original;self.type_value=original.type_value;self.capture_order_value=original.capture_order_value;self.values={};self.calls=0;self.duplicates=0;self.lookup_seconds=0.;self.insert_seconds=0.;self.eval_seconds=0.;self.duplicate_eval_seconds=0.;self.examples=[]
 def evaluate(self,state):
  pos=state.position;tick=time.perf_counter();old=self.values.get(pos);self.lookup_seconds+=time.perf_counter()-tick
  tick=time.perf_counter();v=self.original.evaluate(state);duration=time.perf_counter()-tick;self.calls+=1;self.eval_seconds+=duration
  if old is not None:
   self.duplicates+=1;self.duplicate_eval_seconds+=duration;assert old==v
   if len(self.examples)<3:self.examples.append({'position':record_value(pos),'ply':state.ply_count,'terminal':record_value(state.terminal_status),'value':v})
  else:
   tick=time.perf_counter();self.values[pos]=v;self.insert_seconds+=time.perf_counter()-tick
  return v
limits=SearchLimits(max_depth=3,max_nodes=4096,max_time_seconds=2,quiescence_max_depth=0,quiescence_hard_max_depth=0)
for w in inputs['worlds']:
 if time.perf_counter()-start>=60:break
 c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(w['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(w['initial_record'])));player=AlphaBetaPlayer(c,use_disk_cache=False);trace=Trace(player._evaluator);player._evaluator=trace
 before=s.state,s.to_record(),s._search_witnesses;row={'seed':w['seed'],'root_record':record_value(s.to_record()),'limits':record_value(limits)};out['rows'].append(row);write_record(p/'eval-repeat-results.json',out);tick=time.perf_counter()
 try:
  decision=player.choose_action(s,limits);row['decision']=record_value(decision);row['query_seconds']=time.perf_counter()-tick
 except Exception as exc:row['failure']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
 row.update(calls=trace.calls,duplicates=trace.duplicates,unique_positions=len(trace.values),lookup_seconds=trace.lookup_seconds,insert_seconds=trace.insert_seconds,evaluation_seconds=trace.eval_seconds,duplicate_evaluation_seconds=trace.duplicate_eval_seconds,duplicate_examples=trace.examples);out['wall_seconds']=time.perf_counter()-start;write_record(p/'eval-repeat-results.json',out)
 assert before==(s.state,s.to_record(),s._search_witnesses)
 print('REPEAT',w['seed'],trace.calls,trace.duplicates,round(row.get('query_seconds',0),4),flush=True)
out['unattempted_seeds']=[w['seed'] for w in inputs['worlds'] if w['seed'] not in {r['seed'] for r in out['rows']}];out['wall_seconds']=time.perf_counter()-start;write_record(p/'eval-repeat-results.json',out)
