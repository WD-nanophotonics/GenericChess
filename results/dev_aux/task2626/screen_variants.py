"""Outcome-blind, fixed-index legal-activation screen for task2433 rules 0..15."""
from __future__ import annotations
import hashlib,json,sys,time
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from tools.local_agent.environment import require_identity

OUT=ROOT/'results/dev_aux/task2626/task2433-variant-screen.json'
NODE_CAP_PER_RULE=20000
DEPTH_CAP=24
TIME_CAP_PER_RULE=30.0

def clone(s):
 t=object.__new__(GameSession)
 for k in type(s).__slots__:setattr(t,k,getattr(s,k))
 return t
def p_to_r(s):return any(p is not None and p.base_type_id=='P' and p.current_type_id=='R' for p in s.state.position.board)
def main():
 require_identity()
 if OUT.exists():raise FileExistsError('variant screen is write-once')
 inputs=json.loads((ROOT/'results/dev_aux/task2433/inputs.json').read_text(encoding='utf-8'))
 input_by_index={r['index']:r for r in inputs};all_rows=[];selected=None;began_all=time.perf_counter()
 for index in range(16):
  rel=f'results/dev_aux/task2433/rules-{index}.json';path=ROOT/rel;raw=path.read_bytes()
  compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)));start=GameSession(compiled)
  q=deque([(start,[])]);seen={start.state.position};expanded=0;generated=0;p_moves=0;p_captures=0;maxdepth=0;depth_counts={};witness=None
  began=time.perf_counter()
  while q and expanded<NODE_CAP_PER_RULE and time.perf_counter()-began<TIME_CAP_PER_RULE:
   state,actions_path=q.popleft();depth=len(actions_path);maxdepth=max(maxdepth,depth);depth_counts[depth]=depth_counts.get(depth,0)+1
   if depth>=DEPTH_CAP:continue
   legal=state.legal_actions();expanded+=1;pos=state.state.position
   for action in legal:
    is_p=getattr(action,'actor_type_id',None)=='P'
    if is_p:
     p_moves+=1;to=action.to_square;target=pos.board[to.rank*4+to.file]
     if target is not None and target.owner!=getattr(action,'player',0):p_captures+=1
    child=clone(state);child.submit(action);generated+=1
    path=actions_path+[action_to_dict(action)]
    if p_to_r(child):
     witness={'plies':len(path),'actions':path,'record':json.loads(serialize_game_record(child.to_record()))}
     break
    if not any(p is not None and p.owner==0 and p.base_type_id=='P' and p.current_type_id=='P' for p in child.state.position.board):continue
    key=child.state.position
    if key not in seen:seen.add(key);q.append((child,path))
   if witness:break
  status='WITNESS_FOUND' if witness else 'EXHAUSTED_POSITION_GRAPH' if not q else 'CAP_REACHED'
  row={'index':index,'rule_path':rel,'rule_sha256':hashlib.sha256(raw).hexdigest(),
   'prefit_input_index':input_by_index[index]['index'],'prefit_full_record_sha256':hashlib.sha256(json.dumps(input_by_index[index]['record'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
   'status':status,'expanded_positions':expanded,'unique_positions':len(seen),'generated_transitions':generated,
   'legal_P_moves':p_moves,'legal_P_capture_actions':p_captures,'max_expanded_depth':maxdepth,
   'expanded_by_depth':depth_counts,'frontier_remaining':len(q),'seconds':time.perf_counter()-began,'witness':witness}
  all_rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('witness','expanded_by_depth')},sort_keys=True),flush=True)
  if witness:
   selected=index;break
 result={'status':'FIXED_ORDER_OUTCOME_BLIND_MECHANISM_SCREEN_COMPLETE' if selected is not None else 'NO_WITNESS_WITHIN_SCREEN_CAP',
  'selection_rule':'First task2433 file index with a fully legal P base-to-R current transition under a complete GameSession history; no W/L, search targets, fitness, or model values.',
  'selected_index':selected,'candidate_sha256':None if selected is None else all_rows[-1]['rule_sha256'],
  'records':all_rows,'limits':{'per_rule_node_cap':NODE_CAP_PER_RULE,'depth_cap':DEPTH_CAP,'per_rule_time_cap_seconds':TIME_CAP_PER_RULE},
  'seconds':time.perf_counter()-began_all,
  'negative_scope':'Position-only dedup retains shortest paths; absent a positive witness this is not a complete repetition-history proof. Positive witness is a complete actual GameSession record.'}
 with OUT.open('xb') as f:f.write(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()+b'\n')
 print(json.dumps({'status':result['status'],'selected_index':selected,'tested_rules':len(all_rows),'seconds':result['seconds']},indent=2))
if __name__=='__main__':main()
