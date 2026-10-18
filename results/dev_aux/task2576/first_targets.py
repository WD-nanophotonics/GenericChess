"""Same-initial-theta FIRST TRAIN root targets, all four seeds."""
from pathlib import Path
import json
from math import tanh
def run(directory="results/dev_aux/task2576"):
 d=Path(directory);first={}
 for q in map(json.loads,(d/"queries.jsonl").open()):
  if q["index"]==0 and q["ply"]==0:first[q["seed"],q["method"]]=q
 rows=[]
 for seed in(1977,8173,27182,31415):
  a,b=[first.get((seed,m))for m in("TD_plain","TD_q2")]
  if a is None or b is None:rows.append(dict(seed=seed,status="MISSING_ROOT_QUERY"));continue
  assert a["weights"]==b["weights"]and a["record_before"]==b["record_before"]and a["ordering_seed"]==b["ordering_seed"]and a["actor"]==b["actor"]==a["color"]==b["color"]==0
  def project(q):
   return dict(complete=q["complete"],nodes=q["nodes"],value=q["value"],prediction=None if not q["complete"]else tanh(q["value"]/10.),PV_phi=q["pv_phi"],PV_terminal=q["pv_terminal"],action=None if not q["complete"]else q["record_after"]["moves"][-1],search_stats=q["search_stats"])
  rows.append(dict(seed=seed,status="SAME_INITIAL_MODEL_ROOT_AND_ORDER",initial_weights=a["weights"],plain=project(a),q2=project(b),same_action=a["record_after"]==b["record_after"],same_search_value=a["value"]==b["value"],same_PV_features=a["pv_phi"]==b["pv_phi"]))
 r=dict(status="PASS_ALL_PREFROZEN_FIRST_ROOT_BINDINGS",distinct_full_roots=len({json.dumps(q["record_before"],sort_keys=True)for q in first.values()}),rows=rows,scope="Deterministicindex0/ply0diagnostic designedwhileTRAINactive, beforeanynewEVALfitness; allseedsincludingresourcefailures. Same firstTRAINroot sharedacrossinitials, notfourindependentstates. Internalheuristictargetchangeatidenticalinitialtheta/history/order, nottargetaccuracy/policystrength/causalexplanationoflatertraining. Candidate0onlyfirstroot, no role-generalclaim.")
 (d/"first-targets.json").write_text(json.dumps(r,indent=2));print(json.dumps(dict(status=r["status"],rows=[dict(seed=r["seed"],status=r["status"],same_action=r.get("same_action"),same_search_value=r.get("same_search_value"),same_PV_features=r.get("same_PV_features"))for r in rows])))
if __name__=="__main__":run()
