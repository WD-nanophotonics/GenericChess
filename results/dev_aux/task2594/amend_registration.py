"""Pre-run amendment for exact task2568 runner contract and evidence pins."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; TASK=Path(__file__).resolve().parent; TRAIN=TASK/"train"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    if (TRAIN/"started.json").exists() or (TASK/"eval-started.json").exists(): raise RuntimeError("cannot amend after any run starts")
    regp=TASK/"registration.json"; planp=TRAIN/"plan.json"
    reg=json.loads(regp.read_text()); plan=json.loads(planp.read_text())
    prev=TASK/"registration-v2.json"
    if not prev.exists():
        old=dict(reg);old["status"]="SUPERSEDED_BEFORE_START";old["superseded_by"]="registration.json v3";prev.write_text(json.dumps(old,indent=2)+"\n")
    base_paths=["results/dev_aux/task2568/result.json","results/dev_aux/task2568/credit-sources.json","results/dev_aux/task2568/plan.json","results/dev_aux/task2568/registration.json","results/dev_aux/task2568/eval-plan.json","results/dev_aux/task2568/eval-result.json","results/dev_aux/task2570/eval-plan.json","results/dev_aux/task2570/eval-result.json","results/dev_aux/task2565/chess/plan.json"]
    code_paths=["results/dev_aux/task2594/prepare.py","results/dev_aux/task2594/amend_registration.py"]
    for name in base_paths+code_paths: plan["pins"][name]=sha(ROOT/name)
    seeds=plan["seeds"]
    plan.update({"arms_order":[[s,"TD"] for s in seeds],"nodes_per_arm":1000000,"nodes_per_game":25000,"nodes_per_query":8192,"seconds_per_query":2,"cap_seconds":1200,"max_games":160,"training_family_offset":601000,"prefix_plies":8,"H":1024,"depth":2,"foe":[1.0,1.0,1.0,1.0,1.0],"eta":0.05,"lambda":0.95,"snapshot_nodes":[],"ordering_seed_offset":972568000})
    plan["candidate"]=plan["candidate"]+" Runner contract explicitly exposes task2568.train.run top-level input keys; all values mirror the registered conditions above."
    result=json.loads((ROOT/base_paths[0]).read_text()); credit=json.loads((ROOT/base_paths[1]).read_text())
    td={a["seed"]:a for a in result["arms"] if a["method"]=="TD"}
    counts={str(s):credit["by_arm"][f"({s}, 'TD')"]["target_source_counts"]["terminal_PV_search"] for s in seeds}
    baseline_seconds=sum(a["seconds"] for a in td.values())
    plan["cost"]["baseline_training_seconds_already_paid"]=baseline_seconds
    plan["decision_rule"]["baseline_terminal_targets"]=f"Pinned task2568 TD endpoints: {sum(counts.values())} pooled; per seed {counts}"
    plan["baseline_artifacts"]={p:sha(ROOT/p) for p in base_paths}
    plan["source_base_commit"]=reg["source_base_commit"]
    planp.write_text(json.dumps(plan,indent=2)+"\n")
    newreg={"status":"REGISTERED_AMENDED_BEFORE_TRAIN_AND_FITNESS","version":3,"task":"DEV_AUX2594","session_id":reg["session_id"],"registered_at_utc":reg["registered_at_utc"],"amended_at_utc":datetime.now(timezone.utc).isoformat(),"question":plan["question"],"amendment_reason":"Before any run, pinned the exact reused baseline data and corrected the plan to expose the frozen runner's required top-level contract. No training/fitness was started; scientific conditions and decision criteria are unchanged.","supersedes":"registration-v2.json","source_base_commit":reg["source_base_commit"],"plan_sha256":sha(planp),"eval_plan_sha256":sha(TASK/"eval-plan.json"),"root_manifest_sha256":sha(TASK/"root-manifest.json"),"candidate_source_sha256":plan["pins"]["results/dev_aux/task2593/episode.py"],"runner_sha256":plan["pins"]["results/dev_aux/task2594/train_candidate.py"],"amendment_source_sha256":sha(TASK/"amend_registration.py"),"baseline_artifact_hashes":plan["baseline_artifacts"],"baseline_training_seconds_already_paid":baseline_seconds,"baseline_terminal_targets":counts,"roots":{"train_families":80,"eval_families":128,"evaluation_slots":len(json.loads((TASK/"eval-plan.json").read_text())["slots"]),"unique_disjoint":True},"estimated_total_minutes":84,"science":"OPEN; no training or fitness result is available at registration."}
    regp.write_text(json.dumps(newreg,indent=2)+"\n")
    print(json.dumps({"status":newreg["status"],"baseline_seconds":baseline_seconds,"baseline_targets":counts,"training_contract_keys":["arms_order","nodes_per_arm","nodes_per_game","nodes_per_query","seconds_per_query","cap_seconds","max_games","training_family_offset","prefix_plies","H","depth","foe","eta","lambda","snapshot_nodes"],"plan_sha256":newreg["plan_sha256"],"amendment_source_sha256":newreg["amendment_source_sha256"]},indent=2))
if __name__=="__main__":main()
