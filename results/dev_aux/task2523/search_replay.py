"""Predeclared first4queries/arm replay; not a fresh training or external engine."""
from pathlib import Path
import json,math,time,chess
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def run():
 base=Path('results/dev_aux/task2521');out=Path('results/dev_aux/task2523');plan=json.loads((base/'plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd());stop();first={};records={};start=time.perf_counter();checks=[]
 for line in(base/'episodes.jsonl').open():
  e=json.loads(line)
  if e['game']==0:records[(e['seed'],e['method'])]=e['initial_record']
 for line in(base/'decisions.jsonl').open():
  d=json.loads(line);key=d['seed'],d['method']
  if d['game']==0 and d['ply']<4:first.setdefault(key,[]).append(d)
 for slot in plan['arms']:
  key=slot['seed'],slot['method'];ds=first[key];record=records[key];b=chess.Board(record['initial'])
  for u in record['moves']:b.push_uci(u)
  for d in ds:
   env=ChessEnv(b);m=Model(d['weights_before']);r=TrainingSearch(plan['depth'],quiet=False).search(env,m,nodes=d['effective_node_limit'],seconds=d['effective_wall_limit'],seed=d['seed']*100000+d['ply'],cancel=stop);assert r.complete==d['complete'];assert r.nodes==d['nodes']and r.value==d['value']and r.pv_phi==(None if d['pv_phi']is None else tuple(d['pv_phi']))and r.pv_terminal==d['pv_terminal'];assert(None if r.action is None else r.action.uci())==d['action'];assert env.record()==ChessEnv(b).record()
   if d['method']=='tree':
    samples=[[list(s.phi),None if s.lower==-math.inf else s.lower,None if s.upper==math.inf else s.upper,s.depth]for s in r.samples];assert samples==d['samples']
   checks.append(dict(seed=d['seed'],method=d['method'],ply=d['ply'],nodes=r.nodes,interior_nodes=len(r.samples),complete=r.complete))
   if r.complete:b.push(r.action)
 record=dict(status='PASS_PREDECLARED_FIRST4_QUERIES_PER_ARM',queries=len(checks),nodes=sum(r['nodes']for r in checks),receipts=checks,seconds=time.perf_counter()-start,scope='Samefrozensearch/rulelibrary rerun atoriginalrecorded effectivebudgets, actualaction/node/value/PV/fullTreesamples exact. Onlyfirst4queries perarm, notallsearches/allbudgets/externalengine/generalproof. Modelbefore eachquery replayed, no training restart/extra fitness.');(out/'search-replay.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items()if k!='receipts'}))
if __name__=='__main__':run()
