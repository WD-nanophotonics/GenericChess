"""Capped legal-transition reachability check for the task2433 P-to-R effect."""
from __future__ import annotations
import hashlib,json,sys,time
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_to_dict
from tools.local_agent.environment import require_identity

OUT=ROOT/'results/dev_aux/task2626/promotion-reachability-v5.json'
RULE=ROOT/'results/dev_aux/task2433/rules-0.json'
NODE_CAP=200_000
DEPTH_CAP=64
TIME_CAP=120.0

def promoted(s):
 p=s.state.position
 return [(x.base_type_id,x.current_type_id,x.promoted) for x in p.board if x is not None and
   (x.promoted or x.current_type_id!=x.base_type_id)]
def clone(s):
 t=object.__new__(GameSession)
 for name in type(s).__slots__:setattr(t,name,getattr(s,name))
 return t
def main():
 require_identity()
 if OUT.exists():raise FileExistsError('promotion reachability is write-once')
 raw=RULE.read_bytes();compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
 start=GameSession(compiled);queue=deque([(start,[])])
 # For search efficiency, merge equal complete Positions while retaining the
 # shortest legal path. A positive witness is still replayed under full history.
 # This approximation can only weaken a negative bounded result.
 def state_key(s):return s.state.position
 seen={state_key(start)}
 began=time.perf_counter();expanded=0;generated=0;pruned_dead_pawn=0;max_depth=0;result=None;depth_counts={}
 p_legal=0;p_capture_legal=0;p_effect_action=0
 while queue and expanded<NODE_CAP and time.perf_counter()-began<TIME_CAP:
  state,path=queue.popleft();depth=len(path);max_depth=max(max_depth,depth);depth_counts[depth]=depth_counts.get(depth,0)+1
  if depth>=DEPTH_CAP:continue
  actions=state.legal_actions();expanded+=1
  pos=state.state.position
  for action in actions:
   is_p=getattr(action,'actor_type_id',None)=='P'
   if is_p:
    p_legal+=1;to=action.to_square;idx=to.rank*4+to.file;target=pos.board[idx]
    if target is not None and target.owner!=0:p_capture_legal+=1
   child=clone(state);child.submit(action);generated+=1
   after=promoted(child)
   a=action_to_dict(action)
   if after:
    if is_p:p_effect_action+=1
    result={'status':'LEGAL_PROMOTION_WITNESS_FOUND','plies':depth+1,'actions':path+[a],
      'last_action':a,'promoted_pieces':after,'record':child.to_record().to_dict() if hasattr(child.to_record(),'to_dict') else None}
    # Store the canonical serialized authority record in case the typed record
    # does not expose a mapping conversion.
    try:
     from generic_chess.session.serialization import serialize_game_record
     result['record']=json.loads(serialize_game_record(child.to_record()))
    except Exception:result['record']=None
    break
   # A captured/removed base pawn cannot later produce this P-to-R event:
   # task2433 disallows P drops and has no effect that creates a P.
   live_p=any(p is not None and p.owner==0 and p.base_type_id=='P' and p.current_type_id=='P'
              for p in child.state.position.board)
   if not live_p:
    pruned_dead_pawn+=1;continue
   if depth+1<DEPTH_CAP:
    key=state_key(child)
    if key not in seen:seen.add(key);queue.append((child,path+[a]))
  if result:break
 outcome='FOUND' if result else 'NOT_FOUND_WITHIN_CAP'
 receipt={'status':outcome,'candidate_rule':'results/dev_aux/task2433/rules-0.json',
  'candidate_sha256':hashlib.sha256(raw).hexdigest(),'expanded_states':expanded,'generated_transitions':generated,
  'depth_cap':DEPTH_CAP,'node_cap':NODE_CAP,'time_cap_seconds':TIME_CAP,'maximum_expanded_depth':max_depth,
  'unique_position_repetition_states':len(seen),'expanded_by_depth':depth_counts,'pruned_dead_pawn_transitions':pruned_dead_pawn,
  'legal_P_action_occurrences':p_legal,'legal_P_capture_action_occurrences':p_capture_legal,
  'P_to_R_effect_action_occurrences':p_effect_action,'frontier_remaining':len(queue),
  'dedup_key':'complete Position including auxiliary/hands/side; shortest path retained. This is a reachability search heuristic, not a negative proof about repetition-history variants; any positive witness is a complete replayed GameSession record.',
  'seconds':time.perf_counter()-began,'search_result':result,
  'selection_inputs':'Legal GameSession transitions, current/base piece types and promotion marker only. No outcomes, search scores, weights, or fitness queries.'}
 with OUT.open('xb') as f:f.write(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()+b'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k!='search_result'}|{'witness_plies':None if result is None else result['plies']},indent=2))
if __name__=='__main__':main()
