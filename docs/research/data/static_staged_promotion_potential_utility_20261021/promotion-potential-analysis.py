from __future__ import annotations
import collections,hashlib,json,statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
PLAN=json.loads((HERE/"promotion-potential-plan.json").read_text(encoding="utf-8"))
RUN=HERE/"promotion-potential-run"
GAMES=[json.loads(x) for x in (RUN/"games.jsonl").read_text(encoding="utf-8").splitlines() if x]
RESULT=json.loads((RUN/"result.json").read_text(encoding="utf-8"))
ROOT_LIST=json.loads((RUN/"roots.json").read_text(encoding="utf-8"))
ROOTS={r["root_id"]:r for r in ROOT_LIST}
assert RESULT["status"]=="COMPLETE" and len(GAMES)==PLAN["physical_games"]==64
assert RESULT["invalid_actions"]==RESULT["replay_mismatches"]==RESULT["unstarted_slots"]==0
assert len({g["game_id"] for g in GAMES})==64 and len(ROOTS)==16
by=collections.defaultdict(dict)
for g in GAMES: by[(g["root_id"],g["candidate_owner"])][g["variant"]]=g
assert len(by)==32 and all(set(x)=={"promotion_gain_off","rule_derived_promotion_gain_on"} for x in by.values())
def first(g): return next((m for m in g["moves"] if m["role"]=="candidate"),None)
pairs=[]
for (rid,owner),arms in by.items():
 off=arms["promotion_gain_off"]; on=arms["rule_derived_promotion_gain_on"]
 assert off["root_state_sha256"]==on["root_state_sha256"]
 a,b=first(off),first(on); same=a is not None and b is not None and a["state_before"]==b["state_before"]
 low=(-1 if on["reward"] is None else on["reward"])-(1 if off["reward"] is None else off["reward"])
 high=(1 if on["reward"] is None else on["reward"])-(-1 if off["reward"] is None else off["reward"])
 root=ROOTS[rid]
 pairs.append({"root_id":rid,"seed":root["seed"],"prefix_plies":root["prefix_plies"],
   "parity":"odd" if root["prefix_plies"]%2 else "even","owner":owner,"low":low,"high":high,
   "nodes_off":off["candidate_nodes"],"nodes_on":on["candidate_nodes"],
   "candidate_seconds_off":sum(m["elapsed_seconds"] for m in off["moves"] if m["role"]=="candidate"),
   "candidate_seconds_on":sum(m["elapsed_seconds"] for m in on["moves"] if m["role"]=="candidate"),
   "caller_seconds_off":off["caller_seconds"],"caller_seconds_on":on["caller_seconds"],
   "node_reduction":(off["candidate_nodes"]-on["candidate_nodes"])/max(off["candidate_nodes"],1),
   "unknown_on":on["reward"] is None,"unknown_off":off["reward"] is None,
   "first_state_equal":same,"first_action_changed":bool(same and a["action"]!=b["action"])})
def summary(xs):
 if not xs:return {"n":0}
 n=len(xs)
 return {"n":n,"utility_lower":sum(r["low"] for r in xs)/n,"utility_upper":sum(r["high"] for r in xs)/n,
   "median_candidate_node_reduction":statistics.median(r["node_reduction"] for r in xs),
   "nodes_off":sum(r["nodes_off"] for r in xs),"nodes_on":sum(r["nodes_on"] for r in xs),
   "candidate_seconds_off":sum(r["candidate_seconds_off"] for r in xs),"candidate_seconds_on":sum(r["candidate_seconds_on"] for r in xs),
   "caller_seconds_off":sum(r["caller_seconds_off"] for r in xs),"caller_seconds_on":sum(r["caller_seconds_on"] for r in xs),
   "unknown_pairs":sum(r["unknown_on"] or r["unknown_off"] for r in xs),
   "first_state_comparable":sum(r["first_state_equal"] for r in xs),"first_action_changes":sum(r["first_action_changed"] for r in xs)}
views={"all":pairs,"owner0":[r for r in pairs if r["owner"]==0],"owner1":[r for r in pairs if r["owner"]==1],
       "odd":[r for r in pairs if r["parity"]=="odd"],"even":[r for r in pairs if r["parity"]=="even"]}
summaries={k:summary(v) for k,v in views.items()}
loo=[{"omitted_seed":seed,**summary([r for r in pairs if r["seed"]!=seed])} for seed in sorted({r["seed"] for r in pairs})]
utility_gate=all(summaries[k]["utility_lower"]>0 for k in views) and all(r["utility_lower"]>0 for r in loo)
cost_gate=all(summaries[k]["median_candidate_node_reduction"]>=.10 for k in views) and all(summaries[k]["utility_lower"]>=0 for k in views)
analysis={"schema":"primary-promotion-potential-analysis-v1",
 "plan_sha256":hashlib.sha256((HERE/"promotion-potential-plan.json").read_bytes()).hexdigest().upper(),
 "source_head":RESULT["source_head"],"slots":len(GAMES),"terminals":RESULT["actual_terminals"],
 "unknown_slots":RESULT["unknown"],"invalid_actions":RESULT["invalid_actions"],
 "replay_mismatches":RESULT["replay_mismatches"],"unstarted_slots":RESULT["unstarted_slots"],
 "terminal_reasons":dict(collections.Counter(g["terminal_reason"] for g in GAMES)),
 "rewards":{v:dict(collections.Counter(str(g["reward"]) for g in GAMES if g["variant"]==v)) for v in ("promotion_gain_off","rule_derived_promotion_gain_on")},
 "root_bonus_exposure":{"n":len(ROOT_LIST),"nonzero_roots":sum(r["promotion_bonus_delta"]!=0 for r in ROOT_LIST),
   "deltas":dict(collections.Counter(str(r["promotion_bonus_delta"]) for r in ROOT_LIST))},
 "summary":summaries,"leave_one_seed_out":loo,"utility_gate":utility_gate,"cost_gate":cost_gate,
 "retain_scoped_candidate":utility_gate or cost_gate,"pairs":pairs,
 "per_seed":[{"seed":seed,**summary([r for r in pairs if r["seed"]==seed])} for seed in sorted({r["seed"] for r in pairs})],
 "limits":"Finite generated 5x5 sample; scoped price-derived promotion-potential feature only; no default or broad price-law claim."}
print(json.dumps({k:v for k,v in analysis.items() if k not in ("pairs","leave_one_seed_out","per_seed")},sort_keys=True))
(RUN/"analysis.json").write_text(json.dumps(analysis,indent=2,sort_keys=True)+"\n",encoding="utf-8")
