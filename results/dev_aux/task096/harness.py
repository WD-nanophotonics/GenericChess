import hashlib,json,math,random,sys,time
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/".local_agent/pinned_bebe"));sys.path.insert(1,str(R))
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native import semantic as ns
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict,action_from_dict
from scripts.research_record import record_value
c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c)
TYPES=("N","B","R","Q")
def stop_check():
 for root in (R/".local_agent",Path(r"C:\Users\wdai\Documents\ChatGPT\GenericChess 2\.local_agent")):
  for name in ("rollout.json","advisor.json","slack.json"):
   d=json.loads((root/name).read_bytes());assert not d.get("user_paused") and not d.get("stopped"),"user stop"
def make_weights(theta):return {"P":208,"K":0,**{k:int(round(208*math.exp(t))) for k,t in zip(TYPES,theta)}}
def make_engine(weights):
 values=tuple(weights[k] for k in n.type_ids)
 return SemanticSearchEngine(c,n,board_values=values,hand_values=(0,)*len(values),dynamic_values=None,tt_megabytes=4)
def make_opening(seed,plies=8):
 s=GameSession(c);rng=random.Random(seed);a=[]
 for _ in range(plies):
  if s.result.status.value!="ongoing":break
  legal=sorted(s.legal_actions(),key=lambda x:json.dumps(action_to_dict(x),sort_keys=True));x=rng.choice(legal);s.submit(x);a.append(action_to_dict(x))
 assert s.result.status.value=="ongoing"
 return {"seed":seed,"actions":a,"root":record_value(s.state)}
def play(weights0,weights1,opening,nodes=512,cap=160,depth=8):
 stop_check();start=time.perf_counter();s=GameSession(c)
 for a in opening["actions"]:s.submit(action_from_dict(a))
 engines=[make_engine(w) for w in (weights0,weights1)];actions=[];metrics=[];error=None
 try:
  for ply in range(cap):
   stop_check()
   if s.result.status.value!="ongoing":break
   before=(s.state,tuple(s.history),s.result);owner=s.state.position.side_to_move;r=engines[owner].search(s,SearchLimits(max_depth=depth,max_nodes=nodes,quiescence_max_depth=0))
   assert before==(s.state,tuple(s.history),s.result),"search mutated session"
   assert r.action is not None and r.action in s.legal_actions(),"missing or illegal returned action"
   assert not r.used_fallback,"unexpected fallback"
   metrics.append({k:getattr(r,k) for k in ("nodes","qnodes","completed_depth","selective_depth","score","termination_reason","elapsed_seconds","used_fallback")});actions.append(action_to_dict(r.action));s.submit(r.action)
 except Exception as x:error=type(x).__name__+": "+str(x)
 status=s.result.status.value;winner=s.result.winner;terminal=status!="ongoing";score=None if not terminal else (.5 if winner is None else (1. if winner==0 else 0.))
 return {"weights0":weights0,"weights1":weights1,"opening":opening,"nodes_per_move":nodes,"max_plies":cap,"max_depth":depth,"qdepth":0,"actions":actions,"metrics":metrics,"terminal":terminal,"status":status,"winner":winner,"white_score":score,"censored":not terminal,"error":error,"final_state":record_value(s.state),"wall_seconds":time.perf_counter()-start}
def write(p,d):p.write_bytes((json.dumps(d,indent=2)+"\n").encode())
