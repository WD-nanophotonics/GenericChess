"""Freeze the DEV_AUX terminal-target TDLeaf Chess probe before training."""
from __future__ import annotations
import hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path
import chess
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2565.train import prefix
ROOT=Path(__file__).resolve().parents[3]
TASK=Path(__file__).resolve().parent
TRAIN=TASK/"train"
SEEDS=[1977,8173,27182,31415]
TRAIN_FAMILIES=list(range(601000,601080))
EVAL_BASES=[611000+32*i for i in range(len(SEEDS))]
OLD_FAMILIES=(list(range(311000,312000))+list(range(411000,412000))+list(range(421001,421009))+list(range(431001,431005)))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def key(obj): return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def record(family):
    env=ChessEnv();prefix(env,0,family,8)
    if env.terminal() is not None: raise RuntimeError(f"terminal prefix {family}")
    return env.record()
def main():
    if (TASK/"registration.json").exists(): raise FileExistsError("registered task exists")
    session=json.loads((ROOT/".local_agent"/"session.json").read_text())
    if session.get("state")!="active": raise RuntimeError("DEV_AUX session inactive")
    if sys.version_info[:3]!=(3,12,14) or chess.__version__!="1.11.2": raise RuntimeError("runtime mismatch")
    prior={key(record(f)) for f in OLD_FAMILIES}
    train={f:record(f) for f in TRAIN_FAMILIES}
    eval_families=[b+j for b in EVAL_BASES for j in range(32)]
    evals={f:record(f) for f in eval_families}
    hashes=[key(r) for r in list(train.values())+list(evals.values())]
    if len(hashes)!=len(set(hashes)): raise RuntimeError("duplicate new root")
    if set(hashes)&prior: raise RuntimeError("new root overlaps prior Chess root")
    manifest={"status":"FROZEN_BEFORE_TRAINING_AND_FITNESS","root_semantics":"ChessEnv start plus exact 8-ply prefix via task2565.train.prefix(gs=0,family,8)","prior_family_ids_checked":OLD_FAMILIES,"prior_root_hash_count":len(prior),"train_records":[{"family":f,"record":train[f],"sha256":key(train[f])} for f in TRAIN_FAMILIES],"eval_families_by_seed":{str(s):list(range(b,b+32)) for s,b in zip(SEEDS,EVAL_BASES)},"eval_records":[{"family":f,"record":evals[f],"sha256":key(evals[f])} for f in eval_families],"unique_and_disjoint":True,"created_utc":datetime.now(timezone.utc).isoformat()}
    (TASK/"root-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    source_paths=["results/dev_aux/task2568/train.py","results/dev_aux/task2568/evaluate.py","results/dev_aux/task2566/tc.py","results/dev_aux/task2492/learning.py","results/dev_aux/task2492/episode.py","results/dev_aux/task2492/adapters.py","results/dev_aux/task2504/search.py","results/dev_aux/task2565/train.py","results/dev_aux/task2392/reader.py","results/dev_aux/task2153/stop_evidence.py","results/dev_aux/task2131/stop_reader.py","results/dev_aux/task109/adapter.py","results/dev_aux/task2593/episode.py","results/dev_aux/task2594/train_candidate.py",
        "results/dev_aux/task2568/result.json",
        "results/dev_aux/task2568/credit-sources.json",
        "results/dev_aux/task2568/plan.json",
        "results/dev_aux/task2568/registration.json",
        "results/dev_aux/task2568/eval-plan.json",
        "results/dev_aux/task2568/eval-result.json",
        "results/dev_aux/task2570/eval-plan.json",
        "results/dev_aux/task2570/eval-result.json",
        "results/dev_aux/task2565/chess/plan.json",
    ]
    pins={name:sha(ROOT/name) for name in source_paths}
    plan={"status":"REGISTERED_BEFORE_TRAIN_AND_FITNESS","task":"DEV_AUX2594","session_id":session["id"],"question":"Does terminal-target-local eligibility lambda improve standard-Chess W-L over frozen TDLeaf(lambda=.95) and the same initialization at equal candidate node cost?","changed_premise":"User selected TD/search bootstrapping as the main method; test one local trace rule on standard Chess before any Generic migration.","candidate":"OutcomeGatedTDLeafEpisode(eta=.05, base_lambda=.95); for residual i, lambda_i=1 only when target row i+1 has pv_terminal=true; otherwise .95. Final known-outcome residual uses .95. UNKNOWN censors final residual; incomplete searches are not observed.","seeds":SEEDS,"initialization":"task2568.train.initial(seed): pawn fixed 1, other four material coefficients Uniform(.5,1.5), same initial vector reused per seed.","training":{"domain":"standard Chess via frozen ChessEnv rules/history","arms":[[s,"TD"] for s in SEEDS],"nodes_per_seed":1000000,"aggregate_nodes":4000000,"family_ids":TRAIN_FAMILIES,"family_assignment":"family=601000+index//2; alternating learner colors; 8-ply prefixes shared across seeds","depth":2,"max_game_nodes":25000,"max_query_nodes":8192,"max_query_seconds":2,"max_plies":1024,"foe_weights":[1.0,1.0,1.0,1.0,1.0],"max_games_per_seed":160,"hard_cap_seconds":1200,"incomplete":"All work paid; no partial arm completion or cap extension."},"evaluation":{"conditions":["initial","frozen task2568 TD(.95) endpoint","candidate endpoint"],"roots":"32 roots per seed; same roots and both colors for all endpoints; 64 slots per endpoint/seed; total 768 slots","family_ids":eval_families,"fresh_rule":"All roots frozen before training and exact-history hashed disjoint from registered prior Chess train/eval and new candidate train roots","depth":2,"foe_weights":[1.0,1.0,1.0,1.0,1.0],"max_plies":1024,"max_query_nodes":8192,"max_query_seconds":2,"hard_cap_seconds":2100,"wld":"Actual ChessEnv termination only; UNKNOWN/missing remain [-1,+1], never imputed."},"decision_rule":{"baseline_terminal_targets":"Existing task2568 TD endpoints: 186 pooled across four seeds; per-seed 37,66,38,45","candidate_exposure":"At least 128 terminal-PV target residuals pooled over four candidate seeds; report per-seed counts; underexposure means no Generic transfer","paired_bound":"Per planned matched (seed,root,color) slot, derive actual learner reward in [-1,1]. Unknown/missing reward remains [-1,+1]; difference interval is candidate interval minus comparator interval. Average lower endpoint over all 256 planned pairs.","adopt_for_generic_transfer_only_if":["Independent update/history/root/cost audits pass","Baseline and candidate pooled terminal-target counts each >=128","Finite paired W-L lower bound >0 vs frozen TD(.95)","Finite paired W-L lower bound >0 vs same initial weights"],"otherwise":"Preserve results, no eval-root tuning, no Generic migration."},"cost":{"baseline_training_seconds_already_paid":496.14,"candidate_training_hard_cap_seconds":1200,"evaluation_hard_cap_seconds":2100,"audit_allowance_seconds":1200,"total_accounted_hard_cap_seconds":4996,"estimated_total_minutes_including_historical_baseline_and_audits":84,"threshold":"Estimated <120 minutes, no prior Dot assessment. If any required run is newly estimated >=120 minutes, seek necessity assessment before that run; do not split to evade.","basis":"task2568 measured 12M train nodes in 1488.49s and task2568+2570 768 eval slots in 1824.18s; four TD baseline arms cost ~496s. New work adds 4M train nodes, 768 eval slots, and bounded audits."},"scope":"Finite Chess engineering validation; not a full historical TreeStrap reproduction, population claim, human-price fit or Generic result.","pins":pins,"root_manifest_sha256":sha(TASK/"root-manifest.json"),"runtime":{"python":"3.12.14","python_chess":"1.11.2","platform":platform.platform()}}
    TRAIN.mkdir(exist_ok=True)
    (TRAIN/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    eval_plan={"session_id":session["id"],"registered_at":datetime.now(timezone.utc).isoformat(),"domain":"chess","rules":[0],"foes":{"uniform":[1.0,1.0,1.0,1.0,1.0]},"slots":[[0,s,f,c,t,"uniform"] for s,b in zip(SEEDS,EVAL_BASES) for t in ("initial","baseline","candidate") for f in range(b,b+32) for c in (0,1)],"depth":2,"H":1024,"prefix_plies":8,"nodes_per_query":8192,"seconds_per_query":2,"ordering_seed_offset":972568000,"cap_seconds":2100,"scope":"All four seeds, three endpoints, same 32 fresh roots and both colors per seed; no DEV selection; preserve UNKNOWN/missing."}
    (TASK/"eval-plan.json").write_text(json.dumps(eval_plan,indent=2)+"\n")
    registration={"status":"REGISTERED_BEFORE_TRAIN_AND_FITNESS","task":"DEV_AUX2594","session_id":session["id"],"registered_at_utc":datetime.now(timezone.utc).isoformat(),"question":plan["question"],"plan_sha256":sha(TRAIN/"plan.json"),"eval_plan_sha256":sha(TASK/"eval-plan.json"),"root_manifest_sha256":sha(TASK/"root-manifest.json"),"candidate_source_sha256":pins["results/dev_aux/task2593/episode.py"],"runner_sha256":pins["results/dev_aux/task2594/train_candidate.py"],"baseline_terminal_targets":{"1977":37,"8173":66,"27182":38,"31415":45,"pooled":186},"roots":{"train_families":len(TRAIN_FAMILIES),"eval_families":len(eval_families),"evaluation_slots":len(eval_plan["slots"]),"unique_disjoint":True},"estimated_total_minutes":84,"science":"OPEN; no training or fitness result is available at registration."}
    (TASK/"registration.json").write_text(json.dumps(registration,indent=2)+"\n")
    print(json.dumps(registration,indent=2))
if __name__=="__main__": main()
