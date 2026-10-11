import json,sys
from pathlib import Path
import chess
R=Path.cwd();B=Path(__file__).resolve().parent;rows=[];failures=[]
def uci(a):
 f,t=a["from"],a["to"];s=chess.square_name(chess.square(*f))+chess.square_name(chess.square(*t));prom=a.get("promotion_target_id");return s+(prom.lower() if prom else "")
for task in ("task093","task096"):
 for p in sorted((R/"results/dev_aux"/task).glob("*.json")):
  d=json.loads(p.read_bytes())
  if not all(k in d for k in ("actions","metrics","final_state","opening")):continue
  try:
   board=chess.Board();first_fide=None
   for j,a in enumerate(d["opening"]["actions"]+d["actions"]):
    m=chess.Move.from_uci(uci(a));assert m in board.legal_moves,(p.name,j,uci(a));board.push(m)
    if first_fide is None and board.outcome(claim_draw=False) is not None:first_fide={"ply":j+1,"termination":board.outcome(claim_draw=False).termination.name,"winner":board.outcome(claim_draw=False).winner}
   final=d["final_state"]["position"];actual=[None if board.piece_at(j) is None else {"owner":0 if board.piece_at(j).color else 1,"type":board.piece_at(j).symbol().upper()} for j in range(64)];expected=[None if x is None else {"owner":x["owner"],"type":x["current_type_id"]} for x in final["board"]];assert actual==expected;assert (0 if board.turn else 1)==final["side_to_move"]
   if d["status"]=="checkmate":assert board.is_checkmate() and d["winner"]==(1 if board.turn else 0)
   if d["status"]=="stalemate":assert board.is_stalemate() and d["winner"] is None
   rows.append({"task":task,"game":p.stem,"plies":len(d["actions"]),"board_turn_equal":True,"project_status":d["status"],"independent_first_automatic_outcome":first_fide,"final_fen":board.fen()})
  except Exception as x:failures.append({"task":task,"game":p.stem,"error":type(x).__name__+": "+str(x)})
out={"complete":not failures,"rows":rows,"count":len(rows),"failures":failures,"scope":"Only completed files available at this invocation; independent chess movement/final-board checks, not replacement labels"};(B/"result.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in out.items() if k!="rows"}))
