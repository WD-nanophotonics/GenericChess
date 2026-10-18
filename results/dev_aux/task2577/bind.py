"""Bind all declared endpoints/initials without choosing a winner."""
from pathlib import Path
import json,hashlib
D=Path("results/dev_aux/task2576");E=Path("results/dev_aux/task2577")
def run():
 p=json.loads((D/"plan.json").read_text());t=json.loads((D/"result.json").read_text())
 from results.dev_aux.task2576.train import initial
 arms=[];source={(a["seed"],a["method"]):a for a in t["arms"]}
 for seed in (1977,8173,27182,31415):
  for method in ("initial","TD_plain","TD_q2"):
   for context in ("plain","q2"):
    if method!="initial"and(seed,method)not in source:continue
    a=source.get((seed,method));w=initial(seed)if method=="initial"else a["weights"]
    arms.append(dict(generator_seed=0,seed=seed,method=method+"|"+context,original_method=method,deploy_context=context,initial=initial(seed),weights=w,actual_training_nodes=0 if a is None else a["nodes"],matched_training_budget=method=="initial"or a["nodes"]==p["nodes_per_arm"]))
 r=dict(arms=arms,training_source=str(D/"result.json"),training_sha=hashlib.sha256((D/"result.json").read_bytes()).hexdigest(),scope="ALL declaredinitials/endpoints; partialendpoint ifanyexplicitlycostmarked, missingarmomittedandEVALslotsremainmissing. No selection.")
 (E/"result.json").write_text(json.dumps(r,indent=2));print(json.dumps(dict(bound_models=len(arms),source_status=t["status"])))
if __name__=="__main__":run()
