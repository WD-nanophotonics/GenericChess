"""Registered fixed-foe receipt-path cost scan; no W/L or fitness outputs."""
from pathlib import Path
import datetime, hashlib, json, random, time
import chess
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import AlphaBeta, Model, TreeStrap
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2392.reader import SharedDeleteStopReader
T=Path("results/dev_aux/task2612")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 assert not (T/"started.json").exists()
 p=json.loads((T/"plan.json").read_text(encoding="utf-8")); reg=json.loads((T/"registration.json").read_text(encoding="utf-8"))
 assert sha(T/"plan.json")==reg["plan_sha256"] and reg["registered_before_execution"]
 for source,digest in p["source_sha256"].items(): assert sha(source)==digest,(source,"source changed")
 started=time.perf_counter(); stop=SharedDeleteStopReader(Path.cwd());stop()
 (T/"started.json").write_text(json.dumps({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"session_id":reg["session_id"],"plan_sha256":reg["plan_sha256"],"source_sha256":p["source_sha256"],"python_chess":chess.__version__},indent=2,sort_keys=True)+"\n",encoding="utf-8")
 rows=[]; status="COMPLETE_COST_ONLY"
 with (T/"arms.jsonl").open("x",encoding="utf-8") as out:
  for seed_index,seed in enumerate(p["seeds"]):
   root=ChessEnv(); rng=random.Random(70000+seed)
   for _ in range(p["opening_plies"]):
    if root.terminal() is not None: break
    root.push(rng.choice(sorted(root.actions(),key=lambda a:a.uci())))
   root_record=root.record(); candidate_color=p["candidate_color_by_seed_index"][seed_index]
   init_rng=random.Random(seed); initial=[1.0]+[init_rng.uniform(.5,1.5) for _ in range(4)]
   for method in p["methods"]:
    stop()
    if time.perf_counter()-started>=p["global_hard_cap_seconds"]: status="PARTIAL_HARD_CAP"; break
    env=ChessEnv();env.restore(root_record)
    model=Model(initial); foe=Model(p["opponent_weights"])
    learner=TreeStrap(.05) if method.startswith("TreeStrap") else TDLeafEpisode(.05,.95)
    if isinstance(learner,TDLeafEpisode): learner.reset()
    all_nodes=candidate_nodes=foe_nodes=searches=complete=partial=internal=learner_updates=0
    ending="NODE_BUDGET_UNKNOWN"
    for ply in range(p["max_plies"]):
     stop()
     if time.perf_counter()-started>=p["global_hard_cap_seconds"]: status="PARTIAL_HARD_CAP";ending="GLOBAL_CAP_UNKNOWN";break
     if env.terminal() is not None: ending="TERMINAL_REACHED_LABEL_CENSORED";break
     actor=env.player(); candidate_turn=(actor==candidate_color)
     search_model=model if candidate_turn else foe
     remaining=p["node_budget_per_arm"]-all_nodes
     if remaining<=0: ending="NODE_BUDGET_UNKNOWN";break
     srch=AlphaBeta(2,0)
     receipt=srch.search(env,search_model,nodes=min(p["max_nodes_per_search"],remaining),seconds=p["seconds_per_search_cap"],seed=seed*100000+ply,cancel=stop)
     all_nodes+=receipt.nodes; searches+=1
     if candidate_turn: candidate_nodes+=receipt.nodes
     else: foe_nodes+=receipt.nodes
     if not receipt.complete:
      partial+=1;ending="SEARCH_LIMIT_UNKNOWN";break
     complete+=1
     if candidate_turn:
      if isinstance(learner,TreeStrap):
       stats=learner.update(model,receipt);internal+=stats["samples"]
      else:
       learner.observe(model,receipt);learner_updates+=1
     env.push(receipt.action)
    if isinstance(learner,TDLeafEpisode): learner.finish(model,None)
    row={"seed":seed,"seed_index":seed_index,"method":method,"candidate_color":candidate_color,"start_history_sha256":hashlib.sha256(json.dumps(root_record,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"ending":ending,"candidate_nodes":candidate_nodes,"fixed_foe_nodes":foe_nodes,"total_nodes":all_nodes,"searches":searches,"complete_searches":complete,"incomplete_searches":partial,"internal_bound_samples":internal,"td_complete_candidate_observations":learner_updates,"wall_seconds":time.perf_counter()-started,"labels_or_weights_recorded":False}
    rows.append(row);out.write(json.dumps(row,sort_keys=True)+"\n");out.flush()
   if status=="PARTIAL_HARD_CAP": break
 result={"task":p["task"],"status":status,"plan_sha256":reg["plan_sha256"],"source_sha256":p["source_sha256"],"started_sha256":sha(T/"started.json"),"wall_seconds":time.perf_counter()-started,"arm_count":len(rows),"arms":rows,"fitness_evaluation":False,"outcomes_or_weights":False,"interpretation":"Cost/path evidence only; no W/L, terminal label or learned parameter was used for comparison."}
 (T/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(result,indent=2))
if __name__=="__main__":run()
