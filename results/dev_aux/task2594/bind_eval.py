"""Bind preregistered learner endpoints for the frozen task2568 evaluator."""
import hashlib,json
from pathlib import Path
TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[2]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=TASK/"result.json"
    if out.exists() or (TASK/"eval-started.json").exists(): raise FileExistsError("evaluation already bound or started")
    plan=json.loads((TASK/"train"/"plan.json").read_text())
    reg=json.loads((TASK/"registration.json").read_text())
    assert reg["status"]=="REGISTERED_AMENDED_BEFORE_TRAIN_AND_FITNESS"
    for path,digest in plan["pins"].items(): assert sha(ROOT/path)==digest,path
    base=json.loads((ROOT/"results/dev_aux/task2568/result.json").read_text())
    cand=json.loads((TASK/"train"/"result.json").read_text())
    assert cand["status"] in ("COMPLETE","PARTIAL_CAP")
    seeds=plan["seeds"]
    base_td={a["seed"]:a for a in base["arms"] if a["method"]=="TD"}
    cand_td={a["seed"]:a for a in cand["arms"] if a["method"]=="TD"}
    arms=[]
    for seed in seeds:
        b=base_td[seed]
        arms.append(dict(b,generator_seed=0,method="baseline"))
        c=cand_td.get(seed)
        if c is not None:
            arms.append(dict(c,generator_seed=0,method="candidate"))
            arms.append(dict(c,generator_seed=0,method="TD"))
        else:
            arms.append(dict(b,generator_seed=0,method="TD"))
    payload={"status":"EVAL_INPUT_BOUND_TO_FROZEN_ENDPOINTS","arms":arms,"candidate_train_status":cand["status"],"candidate_train_sha256":sha(TASK/"train"/"result.json"),"baseline_result_sha256":sha(ROOT/"results/dev_aux/task2568/result.json"),"registration_sha256":sha(TASK/"registration.json"),"eval_plan_sha256":sha(TASK/"eval-plan.json")}
    out.write_text(json.dumps(payload,indent=2)+"\n")
    (TASK/"eval-input-binding.json").write_text(json.dumps({k:v for k,v in payload.items() if k!="arms"},indent=2)+"\n")
    print(json.dumps({"candidate_train_status":cand["status"],"candidate_arms":len(cand["arms"]),"eval_models":len(arms),"candidate_seed_endpoints":sorted(cand_td)},indent=2))
if __name__=="__main__": main()
