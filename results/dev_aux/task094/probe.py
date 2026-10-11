import json,sys,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/".local_agent/pinned_bebe"));sys.path.insert(1,str(R));B=Path(__file__).resolve().parent
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import semantic as ns
from generic_chess.session.session import GameSession
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.actions import action_from_dict
c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);d=json.loads((R/"results/dev_aux/task093/declaration.json").read_bytes());rows=[];aux=GameSession(c).state.position.aux_state
for seed,w in d["starts_weights"].items():
 profile=tuple(w[k] for k in n.type_ids)
 def check(pos,case):
  p=ns.pack_current_position(n,pos,ply_count=0);score=ns.evaluate(n,p,board_values=profile,hand_values=(0,)*len(profile),dynamic_values=(0,0,0));white=sum((1 if piece.owner==0 else -1)*w[piece.current_type_id] for piece in pos.board if piece);expected=white if pos.side_to_move==0 else -white;assert score==expected,(seed,case,score,expected);rows.append({"seed":seed,"case":case,"score":score,"expected":expected})
 for kind in "PNBRQ":
  for owner in (0,1):
   for side in (0,1):
    for square in (10,27,44):
     board=[None]*64;board[0]=Piece(0,"K","K");board[63]=Piece(1,"K","K");board[square]=Piece(owner,kind,kind);check(Position(tuple(board),(Hands(),Hands()),side,c.ruleset_fingerprint,aux),f"{kind}-o{owner}-s{side}-q{square}")
 for owner in (0,1):
  board=[None]*64;board[0]=Piece(0,"K","K");board[63]=Piece(1,"K","K");board[27]=Piece(owner,"P","Q",True);check(Position(tuple(board),(Hands(),Hands()),0,c.ruleset_fingerprint,aux),f"promotedPawnToQueen-o{owner}")
 for j,opening in enumerate(d["train_openings"]+d["heldout_openings"]):
  s=GameSession(c)
  for a in opening["actions"]:s.submit(action_from_dict(a))
  check(s.state.position,f"legal-opening{j}")
out={"complete":True,"rows":rows,"count":len(rows),"scope":"Finite explicit material-only leaf contract, not mature engine, exhaustive domain, search strength, history or C source build attestation","sources":{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/"generic_chess/_native/native_module.c",R/".local_agent/pinned_bebe/generic_chess/native/semantic_engine.py",R/".local_agent/pinned_bebe/generic_chess/native/semantic.py"]}};(B/"result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in out.items() if k!="rows"}))
