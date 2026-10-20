"""Bounded evaluation-path cost scan. No W/L value or parameter is emitted."""
from __future__ import annotations
import hashlib, json, random, time, sys
from pathlib import Path
TASK=Path(__file__).parent
sys.path.insert(0,str(TASK.parents[2]))
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import AlphaBeta, Model

TASK=Path(__file__).parent
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    plan=json.loads((TASK/"plan.json").read_text(encoding="utf-8-sig"))
    started=json.loads((TASK/"started.json").read_text(encoding="utf-8-sig"))
    for name,expected in started["source_sha256"].items():
        if sha(TASK.parents[2]/name)!=expected:
            raise SystemExit(f"source hash mismatch: {name}")
    rng_seeds=[2614001+i for i in range(16)]
    roots=[]
    for root_id,seed in enumerate(rng_seeds):
        env=ChessEnv();rng=random.Random(seed)
        for _ in range(plan["roots"]["opening_plies"]):
            actions=sorted(env.actions(),key=lambda a:a.uci())
            if not actions: break
            env.push(rng.choice(actions))
        roots.append((root_id,seed,env.board.copy(stack=True),env.record()))
    started_at=time.perf_counter()
    model=Model([1.0]*5)
    foe=Model([1.0]*5)
    searcher=AlphaBeta(plan["search"]["depth"],plan["search"]["qdepth"])
    rows=[]
    stream=(TASK/"slots.jsonl").open("w",encoding="utf-8",newline="\n")
    try:
        for root_id,seed,board,record in roots:
            root_digest=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
            for candidate_color in (0,1):
                if time.perf_counter()-started_at>=plan["search"]["global_hard_cap_seconds"]:
                    break
                env=ChessEnv(board)
                budget=plan["search"]["node_budget_per_slot_both_actors"]
                nodes_by_actor=[0,0];queries=complete=partial=plies=0;terminal=False;ply_censored=False
                slot_start=time.perf_counter()
                while plies<plan["search"]["max_plies_per_slot"]:
                    if time.perf_counter()-started_at>=plan["search"]["global_hard_cap_seconds"]:
                        break
                    if env.terminal() is not None:
                        terminal=True
                        break
                    remaining=budget-sum(nodes_by_actor)
                    if remaining<=0: break
                    actor=env.player()
                    active=model if actor==candidate_color else foe
                    r=searcher.search(env,active,nodes=min(plan["search"]["max_nodes_per_search"],remaining),
                                      seconds=plan["search"]["seconds_per_search"],
                                      seed=3000000+root_id*8192+candidate_color*4096+plies)
                    queries+=1;nodes_by_actor[actor]+=r.nodes
                    if not r.complete:
                        partial+=1
                        break
                    complete+=1
                    if r.action is None:
                        break
                    env.push(r.action);plies+=1
                else:
                    ply_censored=True
                row={
                    "slot":len(rows),"root_id":root_id,"root_seed":seed,"root_sha256":root_digest,
                    "candidate_color":candidate_color,"nodes_candidate":nodes_by_actor[candidate_color],
                    "nodes_fixed_foe":nodes_by_actor[1-candidate_color],"nodes_total":sum(nodes_by_actor),
                    "queries":queries,"complete_queries":complete,"incomplete_queries":partial,
                    "plies":plies,"ended_by_rule_terminal":terminal,"ply_cap_reached":ply_censored,
                    "wall_seconds":time.perf_counter()-slot_start
                }
                rows.append(row);stream.write(json.dumps(row,separators=(",",":"))+"\n");stream.flush()
            if time.perf_counter()-started_at>=plan["search"]["global_hard_cap_seconds"]:
                break
    finally:
        stream.close()
    result={
        "task":"DEV_AUX2614","status":"COMPLETE_COST_ONLY" if len(rows)==32 else "PARTIAL_COST_ONLY",
        "slots_planned":32,"slots_completed":len(rows),"wall_seconds":time.perf_counter()-started_at,
        "nodes_total":sum(r["nodes_total"] for r in rows),
        "candidate_nodes_total":sum(r["nodes_candidate"] for r in rows),
        "fixed_foe_nodes_total":sum(r["nodes_fixed_foe"] for r in rows),
        "queries_total":sum(r["queries"] for r in rows),
        "incomplete_queries_total":sum(r["incomplete_queries"] for r in rows),
        "terminal_slots":sum(r["ended_by_rule_terminal"] for r in rows),
        "outcomes_or_weights_emitted":False,
        "plan_sha256":sha(TASK/"plan.json"),
        "started_sha256":sha(TASK/"started.json"),
        "source_sha256":started["source_sha256"],
        "interpretation":"Execution-cost evidence only; terminal winner/draw values, W/L labels and model weights were never emitted."
    }
    (TASK/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("source_sha256",)},indent=2))
if __name__=="__main__": main()
