import json,sys,time,hashlib
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/".local_agent/pinned_bebe"));sys.path.insert(1,str(R));B=Path(__file__).resolve().parent
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.native import semantic as ns
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from scripts.research_record import record_value
c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);s=GameSession(c);weights={"P":208,"N":73,"B":901,"R":149,"Q":397,"K":0};profile=tuple(weights[k] for k in n.type_ids);hand=(0,)*len(profile);out={"complete":False,"type_ids":n.type_ids,"weights":weights,"root":record_value(s.state),"Core_terminal":record_value(s.result),"leaves":[]};start=time.perf_counter()
try:
 for owner in (0,1):
  board=[None]*64;board[0]=Piece(0,"K","K");board[63]=Piece(1,"K","K");board[27]=Piece(owner,"B","B")
  pos=Position(tuple(board),(Hands(),Hands()),0,c.ruleset_fingerprint,s.state.position.aux_state);p=ns.pack_current_position(n,pos,ply_count=0);value=ns.evaluate(n,p,board_values=profile,hand_values=hand,dynamic_values=(0,0,0));expected=901*(1 if owner==0 else -1);assert value==expected,(value,expected);out["leaves"].append(dict(owner=owner,actual=value,expected=expected))
 e=SemanticSearchEngine(c,n,board_values=profile,hand_values=hand,dynamic_values=(0,0,0),tt_megabytes=0);before=(s.state,tuple(s.history),s.result);r=e.search(s,SearchLimits(max_depth=2,max_nodes=128,quiescence_max_depth=0));out["search"]=record_value(r);assert r.action in s.legal_actions();assert before==(s.state,tuple(s.history),s.result);out["restored"]=True;out["complete"]=True
except Exception as x:out["error"]=type(x).__name__+": "+str(x)
out["wall_seconds"]=time.perf_counter()-start;(B/"result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in out.items() if k not in ("root","search")}))
