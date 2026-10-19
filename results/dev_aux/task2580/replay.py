"""Actual first/last observed TRAIN search replay, no model update."""
from pathlib import Path
import json,time,hashlib,sys
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
def run(directory="results/dev_aux/task2580",stop_root=None):
 d=Path(directory);ap=json.loads((d/"replay-plan.json").read_text());p=json.loads((d/"plan.json").read_text());w=json.loads((d/"witness-queries.json").read_text());stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();begin=time.perf_counter();rows=[];nodes=0
 for x in w:
  if time.perf_counter()-begin>=ap["total_wall_seconds"]:break
  q=x["query"];e=restore(0,None,q["record_before"]);quiet=q["actor"]==q["color"]and q["method"]=="TD_q2";s=TrainingSearch(p["depth"],quiet=quiet,q_limit=2);before=e.record();r=s.search(e,Model(q["weights"]),nodes=min(ap["nodes_per_query"],q["effective_nodes"]),seconds=min(ap["seconds_per_query"],ap["total_wall_seconds"]-(time.perf_counter()-begin)),seed=q["ordering_seed"],cancel=stop);nodes+=r.nodes
  assert e.record()==before
  status="REPLAY_RESOURCE_UNKNOWN"
  if r.complete:
   e.push(r.action);assert e.record()==q["record_after"]and r.value==q["value"]and r.pv_terminal==q["pv_terminal"]and(None if r.pv_phi is None else list(r.pv_phi))==q["pv_phi"]and r.nodes==q["nodes"]and s.last_stats==q["search_stats"];status="MATCH_VALUE_ACTION_PV_NODES_QSTATS"
  rows.append(dict(key=x["key"],which=x["which"],gameid=q["gameid"],ply=q["ply"],status=status,nodes=r.nodes,seconds=r.seconds))
 result=dict(status="COMPLETE"if len(rows)==len(w)and all(r["status"].startswith("MATCH")for r in rows)else"PARTIAL_RESOURCE_UNKNOWN",expected=len(w),actual=len(rows),matched=sum(r["status"].startswith("MATCH")for r in rows),nodes=nodes,seconds=time.perf_counter()-begin,plan_sha=hashlib.sha256((d/"replay-plan.json").read_bytes()).hexdigest(),rows=rows,scope=ap["scope"])
 (d/"search-replay.json").write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!="rows"}))
if __name__=="__main__":run(sys.argv[1]if len(sys.argv)>1 else"results/dev_aux/task2580")
