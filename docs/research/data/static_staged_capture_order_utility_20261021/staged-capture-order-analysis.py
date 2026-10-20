import hashlib,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
RUN=Path(__file__).resolve().parent/"staged-capture-order-run-20261021"
BASE=RUN.parent
PLAN=json.loads((BASE/"staged-capture-order-plan.json").read_text(encoding="utf-8"))
GAMES=RUN/"capture-order-games.jsonl"
rows=[json.loads(x) for x in GAMES.read_text(encoding="utf-8").splitlines() if x.strip()]
expected_variants=set(PLAN["arms"]["candidate_arms"])
expected_roots=len(PLAN["rules"]["seeds"])*len(PLAN["roots"]["prefix_plies"])*len(PLAN["roots"]["candidate_owners"])*len(PLAN["arms"]["candidate_arms"])
if len(rows)!=expected_roots: raise SystemExit(f"SLOT_COUNT:{len(rows)}")
keys=[(r["root_id"],r["candidate_owner"],r["variant"]) for r in rows]
if len(keys)!=len(set(keys)): raise SystemExit("DUPLICATE_SLOT")
roots={r["root_id"]:r for r in json.loads((RUN/"roots.json").read_text(encoding="utf-8"))}
if len(roots)!=len(PLAN["rules"]["seeds"])*len(PLAN["roots"]["prefix_plies"]): raise SystemExit("ROOT_COUNT")
pairmap={}
for g in rows:
 if not g["full_history_replay_equal"] or g["action_invalid_count"]:
  raise SystemExit(f"INTEGRITY_FAILURE:{g['game_id']}")

 k=(g["root_id"],g["candidate_owner"])
 pairmap.setdefault(k,{})[g["variant"]]=g
if any(set(p)!=expected_variants for p in pairmap.values()) or len(pairmap)!=32:
 raise SystemExit("PAIR_COMPLETENESS_FAILURE")
expected_pairs={(root,owner) for root in roots for owner in (0,1)}
if set(pairmap)!=expected_pairs: raise SystemExit("PLANNED_ROOT_OWNER_COVERAGE_FAILURE")
def reward_bounds(g):
 return (-1,1) if g["reward"] is None else (int(g["reward"]),int(g["reward"]))
pairs=[]
for (root,owner),arms in sorted(pairmap.items()):
 unit=arms["unit_capture_order"]; static=arms["static_v2_capture_order"]
 if unit["root_state_sha256"]!=static["root_state_sha256"]: raise SystemExit("PAIRED_ROOT_MISMATCH")
 ulo,uhi=reward_bounds(unit); slo,shi=reward_bounds(static)
 root_info=roots[root]
 pairs.append({
  "root_id":root,"seed":root_info["seed"],"root_family":root_info["family"],
  "root_plies":root_info["prefix_plies"],"candidate_owner":owner,
  "candidate_first":owner==(root_info["prefix_plies"]%2),
  "unit_reward":unit["reward"],"static_reward":static["reward"],
  "utility_lower":slo-uhi,"utility_upper":shi-ulo,
  "both_known":unit["reward"] is not None and static["reward"] is not None,
  "unit_candidate_nodes":sum(int(m["nodes"]) for m in unit["moves"] if m["role"]=="candidate"),
  "static_candidate_nodes":sum(int(m["nodes"]) for m in static["moves"] if m["role"]=="candidate"),
  "unit_foe_nodes":sum(int(m["nodes"]) for m in unit["moves"] if m["role"]=="foe"),
  "static_foe_nodes":sum(int(m["nodes"]) for m in static["moves"] if m["role"]=="foe"),
  "unit_candidate_qnodes":sum(int(m["qnodes"]) for m in unit["moves"] if m["role"]=="candidate"),
  "static_candidate_qnodes":sum(int(m["qnodes"]) for m in static["moves"] if m["role"]=="candidate"),
  "unit_candidate_seconds":sum(float(m["elapsed_seconds"]) for m in unit["moves"] if m["role"]=="candidate"),
  "static_candidate_seconds":sum(float(m["elapsed_seconds"]) for m in static["moves"] if m["role"]=="candidate"),
  "unit_foe_seconds":sum(float(m["elapsed_seconds"]) for m in arms["unit_capture_order"]["moves"] if m["role"]=="foe"),
  "static_foe_seconds":sum(float(m["elapsed_seconds"]) for m in arms["static_v2_capture_order"]["moves"] if m["role"]=="foe"),
  "unit_candidate_capture_calls":sum(int(m["capture_order_calls_delta"]) for m in unit["moves"] if m["role"]=="candidate"),
  "static_candidate_capture_calls":sum(int(m["capture_order_calls_delta"]) for m in static["moves"] if m["role"]=="candidate"),
  "unit_foe_capture_calls":sum(int(m["capture_order_calls_delta"]) for m in unit["moves"] if m["role"]=="foe"),
  "static_foe_capture_calls":sum(int(m["capture_order_calls_delta"]) for m in static["moves"] if m["role"]=="foe"),
 })
def util_summary(ps):
 if not ps:return {"n_pairs":0}
 n=len(ps)
 return {"n_pairs":n,"both_known_pairs":sum(x["both_known"] for x in ps),
         "pairs_with_unknown":sum(not x["both_known"] for x in ps),
         "mean_conservative_lower":sum(x["utility_lower"] for x in ps)/n,
         "mean_conservative_upper":sum(x["utility_upper"] for x in ps)/n,
         "lower_sum":sum(x["utility_lower"] for x in ps),
         "upper_sum":sum(x["utility_upper"] for x in ps)}
def node_summary(ps):
 vals=[]
 for x in ps:
  u=x["unit_candidate_nodes"]; s=x["static_candidate_nodes"]
  vals.append((u-s)/max(u,1))
 return {"n_pairs":len(ps),"unit_candidate_nodes":sum(x["unit_candidate_nodes"] for x in ps),
         "static_candidate_nodes":sum(x["static_candidate_nodes"] for x in ps),
         "median_paired_fractional_reduction":statistics.median(vals) if vals else None,
         "median_absolute_node_delta_static_minus_unit":statistics.median([x["static_candidate_nodes"]-x["unit_candidate_nodes"] for x in ps]) if ps else None,
         "pairs_unit_zero":sum(x["unit_candidate_nodes"]==0 for x in ps)}
groups={"overall":pairs}
for owner in (0,1):
 groups[f"owner_{owner}"]=[p for p in pairs if p["candidate_owner"]==owner]
for plies in sorted({p["root_plies"] for p in pairs}):
 groups[f"root_plies_{plies}"]=[p for p in pairs if p["root_plies"]==plies]
for first in (True,False):
 groups[f"candidate_{'first' if first else 'reply'}"]=[p for p in pairs if p["candidate_first"]==first]
metrics={k:{"utility":util_summary(v),"candidate_cost":node_summary(v)} for k,v in groups.items()}
loo={}
for seed in sorted({p["seed"] for p in pairs}):
 sub=[p for p in pairs if p["seed"]!=seed]
 loo[str(seed)]={"utility":util_summary(sub),"candidate_cost":node_summary(sub)}
actual_terminals=sum(g["terminal_reason"]=="ACTUAL_TERMINAL" for g in rows)
unknowns=[g for g in rows if g["reward"] is None]
retained_a=all(metrics[k]["utility"]["mean_conservative_lower"]>0 for k in
 ["overall","owner_0","owner_1","root_plies_3","root_plies_4"]) and all(x["utility"]["mean_conservative_lower"]>0 for x in loo.values())
retained_b=all(metrics[k]["candidate_cost"]["median_paired_fractional_reduction"]>=.10 for k in
 ["overall","owner_0","owner_1","root_plies_3","root_plies_4"]) and all(metrics[k]["utility"]["mean_conservative_lower"]>=0 for k in
 ["overall","owner_0","owner_1","root_plies_3","root_plies_4"])
summary={
 "schema":"primary-static-staged-capture-order-utility-analysis-v1",
 "status":"COMPLETE","session_id":PLAN["session_id"],
 "plan_sha256":hashlib.sha256((BASE/"staged-capture-order-plan.json").read_bytes()).hexdigest(),
 "preflight_sha256":hashlib.sha256((BASE/"staged-capture-order-preflight.json").read_bytes()).hexdigest(),
 "producer_sha256":hashlib.sha256((BASE/"staged-capture-order-producer.py").read_bytes()).hexdigest(),
 "execution_sha256":hashlib.sha256((RUN/"execution-start.json").read_bytes()).hexdigest(),
 "games_sha256":hashlib.sha256(GAMES.read_bytes()).hexdigest(),
 "physical_games":len(rows),"pairs":len(pairs),"actual_terminals":actual_terminals,
 "unknown_slots":len(unknowns),"unknown_reasons":{k:sum(g["terminal_reason"]==k for g in unknowns) for k in sorted({g["terminal_reason"] for g in unknowns})},
 "invalid_actions":sum(g["action_invalid_count"] for g in rows),
 "replay_mismatches":sum(not g["full_history_replay_equal"] for g in rows),
 "type_value_calls":sum(g["type_value_calls"] for g in rows),
 "candidate_capture_calls":{"unit_arm":sum(p["unit_candidate_capture_calls"] for p in pairs),
                            "static_arm":sum(p["static_candidate_capture_calls"] for p in pairs),
                            "foe_calls_across_both_arms":sum(p["unit_foe_capture_calls"]+p["static_foe_capture_calls"] for p in pairs)},
 "candidate_and_foe_nodes":{"unit_arm_candidate":sum(p["unit_candidate_nodes"] for p in pairs),
                            "static_arm_candidate":sum(p["static_candidate_nodes"] for p in pairs),
                            "unit_arm_foe":sum(p["unit_foe_nodes"] for p in pairs),
                            "static_arm_foe":sum(p["static_foe_nodes"] for p in pairs)},
 "candidate_and_foe_seconds":{"unit_arm_candidate":sum(p["unit_candidate_seconds"] for p in pairs),
                              "static_arm_candidate":sum(p["static_candidate_seconds"] for p in pairs),
                              "unit_arm_foe":sum(x["unit_foe_seconds"] for x in pairs),
                              "static_arm_foe":sum(x["static_foe_seconds"] for x in pairs)},
 "strata":metrics,"leave_one_seed_out":loo,
 "retention_gate":{"utility_gate_a":retained_a,"node_saving_gate_b":retained_b,
                   "retain_scoped_candidate":retained_a or retained_b,
                   "scope_claim":"No default/global value or strength claim."},
 "pairs":pairs
}
out=RUN/"analysis.json"
out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({k:summary[k] for k in ("physical_games","pairs","actual_terminals","unknown_slots","unknown_reasons","invalid_actions","replay_mismatches","type_value_calls","candidate_capture_calls","candidate_and_foe_nodes","strata","retention_gate")},sort_keys=True))
