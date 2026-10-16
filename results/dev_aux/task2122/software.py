"""Node-only software qualification of already derived ordinal price cells."""
from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_native_material import _load_transport
from results.dev_aux.task2100.campaign import evaluate
OUT=Path('results/dev_aux/task2122')
def run():
 if (OUT/'software-started.json').exists():raise RuntimeError('no frozen softwarecap restart')
 start=time.perf_counter();deadline=start+180;plan=json.loads((OUT/'plan.json').read_text());(OUT/'software-started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');stop=_load_transport().stop_check
 def cancelled():stop(Path.cwd());return time.perf_counter()>=deadline
 roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'][:32];rows=[];pairs=[]
 for root in roots:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession(c)
  for nodes in plan['normal_node_caps']:
   for a,b in plan['diagnostic_pairs']:
    rr=[]
    for ratio in(a,b):
     d=ProofMaterialPlayer(c,evaluate(ratio),proof_enabled=False,max_depth=3).choose(s.state,max_nodes=nodes,seconds=1.,cancel=cancelled,_clock=lambda:0.)
     if cancelled():raise RuntimeError('original180cap')
     r=dict(family=root['family'],ratio=ratio,node_cap=nodes,choice=None if d.action is None else action_to_dict(d.action),completed_depth=d.completed_depth,nodes=d.search_nodes,source=d.source,exit_cause=d.exit_cause);rr.append(r);rows.append(r)
    same=all(rr[0][k]==rr[1][k]for k in('choice','completed_depth','nodes','source','exit_cause'));assert same;pairs.append(dict(family=root['family'],node_cap=nodes,ratios=[a,b],same_node_traversal_receipt=same))
 result=dict(status='PASS_NODE_ONLY_COLD_SOFTWARE_ORDINAL_CELLS',queries=len(rows),pairs=len(pairs),all_identical=True,seconds=time.perf_counter()-start,clock='Fixed0 clock ONLY for node-cutoff algorithm qualification, actualseparate180wall/stop guard; no timedperformanceclaim or wallpolicy/gameequivalence')
 (OUT/'software-queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'software-pairs.json').write_text(json.dumps(pairs,indent=2),encoding='utf-8');(OUT/'software-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
