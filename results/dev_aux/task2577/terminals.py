"""Actual full-history terminal causes and paired outcome contributions."""
from pathlib import Path
from collections import Counter,defaultdict
import json,itertools,sys
import chess
from results.dev_aux.task2568.summary import bounds
def run(directory="results/dev_aux/task2577"):
 d=Path(directory);p=json.loads((d/"eval-plan.json").read_text());rows={tuple(g["slot"]):g for g in map(json.loads,(d/"eval-games.jsonl").open())};ledger=[];kinds={};groups=defaultdict(Counter)
 for slot in p["slots"]:
  key=tuple(slot);g=rows.get(key)
  if g is None:kind="MISSING"
  else:
   b=chess.Board(g["record"]["initial"])
   for a in g["record"]["moves"]:b.push_uci(a)
   out=b.outcome(claim_draw=True)
   assert(None if out is None else 0 if out.winner is None else 1 if out.winner else-1)==g["outcome"]
   kind="UNKNOWN:"+g["ending"]if out is None else out.termination.name
   ledger.append(dict(slot=slot,kind=kind,actual_terminal=out is not None,reward=g["reward"],played_plies=len(g["record"]["moves"])-len(g["initial_record"]["moves"]),final_fen=b.fen()))
  kinds[key]=kind;groups[slot[4]+"/"+slot[5]][kind]+=1
 pairs={}
 for ctx in sorted({s[4].split("|")[-1]for s in p["slots"]}):
  for left,right in(("TD_plain","initial"),("TD_q2","initial"),("TD_q2","TD_plain")):
   cc=defaultdict(lambda:dict(n=0,lower_sum=0.,upper_sum=0.));cells=[]
   for seed,fam,color,foe in sorted({(s[1],s[2],s[3],s[5])for s in p["slots"]}):
    a=(0,seed,fam,color,left+"|"+ctx,foe);b=(0,seed,fam,color,right+"|"+ctx,foe);aa,bb=bounds(rows.get(a)),bounds(rows.get(b));lo,hi=aa[0]-bb[1],aa[1]-bb[0];label=kinds[a]+" / "+kinds[b];cc[label]["n"]+=1;cc[label]["lower_sum"]+=lo;cc[label]["upper_sum"]+=hi
    cells.append(dict(seed=seed,family=fam,color=color,foe=foe,left_terminal=kinds[a],right_terminal=kinds[b],bounds=[lo,hi]))
   pairs[ctx+"/"+left+"-"+right]=dict(by_terminal_pair=dict(cc),cells=cells)
 r=dict(status="PASS_ACTUAL_RULE_TERMINAL_CLASSIFICATION",actual_rows=len(ledger),missing=len(p["slots"])-len(ledger),by_model_foe=dict(groups),paired_contributions=pairs,ledger=ledger,scope="Actualpythonchess fullhistory andcommonpredeclared claimavailabledrawpolicy; intended-next-move3fold/50moveclaims allowed. Ruleterminaldrawdistinctfromresource/horizonUNKNOWN. No newgames/labels/claimaboutconversionability or independentengine. Pair sums descriptive, allknownsides preserved.")
 (d/"terminal-ledger.json").write_text(json.dumps(r,indent=2));print(json.dumps(dict(status=r["status"],groups=r["by_model_foe"])))
if __name__=="__main__":run(sys.argv[1]if len(sys.argv)>1 else"results/dev_aux/task2577")
