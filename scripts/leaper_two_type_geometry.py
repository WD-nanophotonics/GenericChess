"""Four preregistered dynamic-leaf controls; material/ordering remain unit."""
from pathlib import Path
from dataclasses import replace
import json,time
from scripts import leaper_design as L
from scripts.semantic_probe_cost import unit_evaluator
from scripts.leaper_two_type_forward import now,player
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from tools.local_agent.common import write_json
from tools.local_agent import session

def dynamic_player(c):
 u=unit_evaluator(c);cfg=EvaluationConfig(dynamic_mobility_weight=2,anchor_escape_weight=5,promotion_potential_weight=3);profile=replace(u._profile,config_hash=config_hash(cfg),evaluator_version='explicit-unit-plus-dynamics')
 e=L.LeafOrderAdapter(Evaluator(c,profile,cfg),u)
 return L.AlphaBetaPlayer(c,evaluator_override=e,tuning=SearchTuning(),use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_availability=False,use_native_semantic_check=False),L.record_value(profile),L.record_value(cfg)
def game(world,index,path,deadline):
 assert not path.exists();c=L.compile_rule(L.ruleset_from_dict(world['rule']));root=world['roots'][index];s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])));p,profile,cfg=dynamic_player(c);ps={0:p,1:player(c,1000)};tick=time.perf_counter();start=now();queries=[];censor=None;slot=dict(root=index,policy='DYNAMIC_UNIT',seed=202610242000+index)
 while not s.state.terminal_status.is_terminal:
  if session.stopped():censor='user_stop';break
  if time.perf_counter()>=deadline:censor='whole_cap';break
  side=s.state.position.side_to_move;legal=s.legal_actions();t=time.perf_counter();d=ps[side].choose_action(s,L.SearchLimits(max_depth=64,max_nodes=8192,max_time_seconds=3,quiescence_max_depth=0,quiescence_hard_max_depth=8));q=dict(actor=side,root_ply=s.state.ply_count,state_sha256=L.state_sha(s.state),legal_count=len(legal),decision=L.record_value(d),action=L.record_value(d.action),seconds=time.perf_counter()-t);queries.append(q)
  write_json(path,dict(status='RUNNING',slot=slot,started_at=start,initial_record=root['record'],queries=queries,current_record=L.record_value(s.to_record())))
  if d.action is None:censor='no_action';break
  assert d.action in legal;s.submit(d.action)
 row=dict(status='CLOSED',slot=slot,started_at=start,ended_at=now(),seconds=time.perf_counter()-tick,initial_record=root['record'],queries=queries,final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),censor=censor,value=L.outcome_value(s.result,0,censor),nodes_limit=8192,attacker_profile=profile,attacker_config=cfg)
 write_json(path,row);print('DYNAMIC',index,row['terminal']['status'],row['value'],len(queries),row['seconds'],flush=True);return row
if __name__=='__main__':
 inp=Path('.local_agent/ab-two-type-inputs-frozen.json');plan=Path('.local_agent/ab-geometry-contrast-plan.json');reg=L.load(plan);world=L.load(inp);target=Path('.local_agent/ab-geometry-contrast');assert not target.exists();target.mkdir();tick=time.perf_counter();out=dict(status='RUNNING',started_at=now(),input_sha256=L.sha(inp),plan_sha256=L.sha(plan),source_sha256=L.sha(Path(__file__)),slots=[]);write_json(target/'execution.json',out)
 try:
  for i in reg['roots']:
   if time.perf_counter()-tick>=reg['cap_seconds']:break
   row=game(world,i,target/f'game-{i:03d}.json',tick+reg['cap_seconds']);out['slots'].append(dict(root=i,value=row['value'],seconds=row['seconds'],censor=row['censor']));write_json(target/'execution.json',out)
 finally:
  out.update(status='CLOSED',ended_at=now(),seconds=time.perf_counter()-tick,missing=[i for i in reg['roots']if not any(x['root']==i and x['value']is not None for x in out['slots'])]);write_json(target/'execution.json',out)
