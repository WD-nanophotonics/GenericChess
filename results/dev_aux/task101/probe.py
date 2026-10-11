import json,collections,time
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;rows=[];start=time.perf_counter()
def quantity(b):
 return sum(len(b.pieces(t,True))-len(b.pieces(t,False)) for t in (chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN))
for task in ("task093","task096"):
 for path in sorted((ROOT/"results/dev_aux"/task).glob("*.json")):
  d=json.loads(path.read_bytes())
  if not all(k in d for k in ("actions","metrics","final_state","opening")):continue
  b=chess.Board();first=None;cut=None;oplen=len(d["opening"]["actions"])
  for i,a in enumerate(d["opening"]["actions"]+d["actions"]):
   f,t=a["from"],a["to"];uci=chess.square_name(chess.square(*f))+chess.square_name(chess.square(*t))+(a.get("promotion_target_id") or "").lower();m=chess.Move.from_uci(uci);assert m in b.legal_moves;b.push(m)
   outcome=b.outcome(claim_draw=False)
   if outcome is not None and first is None:first=dict(total_ply=i+1,after_opening_ply=i+1-oplen,termination=outcome.termination.name,winner=outcome.winner,quantity_difference=quantity(b))
   if i+1-oplen==64:cut=dict(quantity_difference=quantity(b),fen=b.fen(),counterfactual_after_standard_terminal=first is not None)
  rows.append(dict(task=task,game=path.stem,project_status=d["status"],project_plies=len(d["actions"]),first_standard_terminal=first,raw64_snapshot=cut))
summary={}
for task in ("task093","task096"):
 cohort=[x for x in rows if x["task"]==task];ends=[x["first_standard_terminal"] for x in cohort if x["first_standard_terminal"] and x["first_standard_terminal"]["after_opening_ply"]<=64];raw=[x["raw64_snapshot"] for x in cohort if x["raw64_snapshot"]]
 summary[task]=dict(games=len(cohort),project_status_counts=dict(collections.Counter(x["project_status"] for x in cohort)),
  first_standard_terminal_within64=dict(collections.Counter(x["termination"] for x in ends)),
  raw64_quantity_histogram=dict(sorted(collections.Counter(x["quantity_difference"] for x in raw).items())),
  raw64_snapshots=len(raw),counterfactual_after_standard_terminal=sum(x["counterfactual_after_standard_terminal"] for x in raw))
result=dict(complete=True,summary=summary,rows=rows,wall_seconds=time.perf_counter()-start,scope="Observed prior project trajectories, not mature/random-player or supervised learning data; no original label changed.")
(OUT/"result.json").write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps(summary))
