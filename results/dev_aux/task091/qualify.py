import hashlib,json,re,sys,time
from pathlib import Path
import chess
from protocol import Protocol
R=Path.cwd();B=Path(__file__).resolve().parent;P=R/".local_agent/material-selfplay";rows=[];start=time.perf_counter()
weights=[dict(p=208,n=73,b=901,r=149,q=397),dict(p=208,n=701,b=89,r=997,q=131)]
text=""
for j,w in enumerate(weights):
 line=" ".join(f"{k}:{v}" for k,v in w.items());text+=f"[aux_qual_{j}:chess]\npieceValueMg = {line}\npieceValueEg = {line}\n\n"
(P/"qualification.ini").write_bytes(text.encode());e=None;out={"complete":False,"weights":weights,"rows":rows,"binary_sha256":hashlib.sha256((P/"fairy-material.exe").read_bytes()).hexdigest()}
try:
 e=Protocol(P/"fairy-material.exe",P);names={x.split("option name ",1)[1].split(" type ",1)[0] for x in e.handshake if x.startswith("option name ")};out["handshake"]=e.handshake
 for name,value in [("Threads",1),("Hash",16),("Use NNUE","false"),("SyzygyPath","<empty>"),("VariantPath",str(P/"qualification.ini"))]:
  assert name in names;e.send(f"setoption name {name} value {value}")
 e.ready()
 for j,w in enumerate(weights):
  e.send(f"setoption name UCI_Variant value aux_qual_{j}");e.ready()
  for kind in "pnbrq":
   for side in ("w","b"):
    fen=f"7k/8/8/3{kind.upper()}4/8/8/8/K7 {side} - - 0 1";board=chess.Board(fen);assert board.is_valid();e.send("position fen "+fen);e.send("eval");lines=e.ready();final=next(x for x in lines if x.startswith("Final evaluation"));value=float(final.split()[2]);expected=w[kind]/208;assert abs(value-expected)<=.011,(value,expected)
    e.send("go nodes 512");search=e.until(lambda x:x.startswith("bestmove "));move=search[-1].split()[1];assert chess.Move.from_uci(move) in board.legal_moves
    rows.append(dict(variant=j,type=kind,side=side,fen=fen,final_eval_pawns=value,expected_white_pawns=expected,bestmove=move,search_info=search))
 out["complete"]=True
except Exception as x:out["error"]=type(x).__name__+": "+str(x)
finally:
 if e:e.close();out["protocol"]=e.raw
 out["wall_seconds"]=time.perf_counter()-start;(B/"qualification.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in out.items() if k not in ("rows","protocol","handshake")}))
 assert out["complete"]
