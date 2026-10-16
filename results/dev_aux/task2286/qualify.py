from pathlib import Path
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task2238.normal import SeededMaterialSearch
from results.dev_aux.task2175.receipt import choice_value
OUT=Path("results/dev_aux/task2286")
def run():
 start=time.perf_counter();p=json.loads((OUT/"plan.json").read_text());stop=EvidenceStopReader(Path.cwd());roots=json.loads(Path("results/dev_aux/task2282/inputs.json").read_text())["roots"];rows=[];pairs=[]
 def cancel():stop();return time.perf_counter()-start>=p["seconds_cap"]
 with(OUT/"queries.jsonl").open("x")as f:
  for root in roots:
   assert root["split"]=="TRAIN";c=compile_ruleset_for_execution(deserialize_ruleset(Path(root["rules"]).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root["record"])))
   for seed in p["seeds"]:
    rr={}
    for ratio in p["profiles"]:
     def ev(pos,t):return float(sum((1 if pc.owner==t else -1)*(ratio if pc.current_type_id=="R"else 1.)for pc in pos.board if pc is not None and pc.current_type_id!="K"))
     d=SeededMaterialSearch(c,ev,max_depth=3,priority_seed=seed).choose(s,max_nodes=50000,seconds=5.,cancel=cancel);assert d.completed_depth==3
     r=dict(family=root["family"],seed=seed,ratio=ratio,choice=choice_value(d.choice),score=str(d.score),nodes=d.nodes,transitions=d.session_transitions,completed_depth=d.completed_depth,seconds=d.seconds);rr[ratio]=r;rows.append(r);f.write(json.dumps(r)+"\n");f.flush()
    for a,b in p["pairs"]:
     assert all(rr[a][k]==rr[b][k]for k in("choice","nodes","transitions","completed_depth"));pairs.append(dict(family=root["family"],seed=seed,pair=[a,b],same=True))
 result=dict(status="PASS_FINITE_MATERIAL_ORDERCELLS_AND_SAME_COMPLETE_D3_EXECUTION",queries=len(rows),within_cell_pairs=len(pairs),boundary_choice_differences=sum(next(r for r in rows if r["family"]==f and r["seed"]==seed and r["ratio"]==2.)["choice"]!=next(r for r in rows if r["family"]==f and r["seed"]==seed and r["ratio"]==x)["choice"]for f in [r["family"]for r in roots]for seed in p["seeds"]for x in(1.5,3.)),seconds=time.perf_counter()-start,scope=p["scope"])
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
