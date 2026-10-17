"""Static-state frozen search directions and initial TRAIN-only RMS calibration."""
from dataclasses import replace
from math import sqrt,isfinite
from pathlib import Path
import json,random,time,hashlib,datetime
from results.dev_aux.task2492.learning import TreeStrap,Model,interval_error,transformed
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
class RootStrap(TreeStrap):
 def update(self,model,receipt):
  if receipt.complete and receipt.samples:
   root=receipt.samples[-1];assert root.lower==root.upper
   receipt=replace(receipt,samples=(root,))
  return super().update(model,receipt)
def direction(model,samples):
 v=[0.]*len(model.weights)
 for s in samples:
  error=interval_error(model.prediction(s.phi),transformed(s.lower,model.scale),transformed(s.upper,model.scale))
  v=[x+error*g for x,g in zip(v,model.gradient(s.phi))]
 return[x/max(1,len(samples))for x in v]
def factor(tree,root):
 assert len(tree)==len(root)>0
 t=sqrt(sum(sum(x*x for x in v)for v in tree)/len(tree));r=sqrt(sum(sum(x*x for x in v)for v in root)/len(root))
 if t<=1e-12 or r<=1e-12:return dict(gate='INSUFFICIENT_INITIAL_GRADIENT_SIGNAL',tree_RMS=t,root_RMS=r,factor=None)
 c=t/r;assert isfinite(c)and c>0;return dict(gate='INITIAL_RMS_CALIBRATED',tree_RMS=t,root_RMS=r,factor=c)
def run():
 out=Path('results/dev_aux/task2517');p=json.loads((out/'plan.json').read_text());assert not(out/'started.json').exists()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();rows=[];tree=[];root=[];status='COMPLETE';nodes=0
 (out/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((out/'plan.json').read_bytes()).hexdigest())))
 with(out/'queries.jsonl').open('x')as f:
  for seed in p['seeds']:
   rng=random.Random(seed);weights=[1.]+[rng.uniform(.5,1.5)for _ in range(4)];model=Model(weights)
   for family in p['families']:
    stop();env=ChessEnv();rng=random.Random(family)
    for _ in range(p['prefix_plies']):
     if env.terminal()is not None:break
     env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
    record=env.record();terminal=env.terminal();remaining=p['cap_seconds']-(time.perf_counter()-start)
    if remaining<=0:status='PARTIAL_CAP';break
    if terminal is not None:r=None;tg=rg=[0.]*5;complete=True
    else:
     effective=min(p['seconds_per_query'],remaining);r=TrainingSearch(p['depth'],quiet=False).search(env,model,nodes=p['nodes_per_query'],seconds=effective,seed=family+p['ordering_seed_offset'],cancel=stop);nodes+=r.nodes;complete=r.complete;tg=direction(model,r.samples)if complete else None;rg=direction(model,r.samples[-1:])if complete else None
    row=dict(seed=seed,family=family,weights=weights,record=record,actual_terminal=terminal,complete=complete,effective_node_limit=None if r is None else p['nodes_per_query'],effective_wall_limit=None if r is None else effective,global_remaining_before_query=remaining,nodes=0 if r is None else r.nodes,seconds=0 if r is None else r.seconds,reason='ACTUAL_TERMINAL_ZERO_GRADIENT'if r is None else r.reason,samples=[]if r is None else[[list(s.phi),None if s.lower==float('-inf')else s.lower,None if s.upper==float('inf')else s.upper,s.depth]for s in r.samples],tree_direction=tg,root_direction=rg);rows.append(row);f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush()
    if complete:tree.append(tg);root.append(rg)
   if status!='COMPLETE':break
 result=factor(tree,root)if status=='COMPLETE'and len(rows)==len(p['seeds'])*len(p['families'])and all(r['complete']for r in rows)else dict(gate='CALIBRATION_UNKNOWN',factor=None)
 result.update(status=status,expected=len(p['seeds'])*len(p['families']),actual=len(rows),nodes=nodes,seconds=time.perf_counter()-start,zero_tree=sum(not any(v)for v in tree),zero_root=sum(not any(v)for v in root),scope=p['scope']);(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
