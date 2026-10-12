"""Posthoc attainable-distance bound for frozen six-perturbation schedule."""
import importlib.util,json,math,random,itertools,statistics,time
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task128';OUT.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('opt128',ROOT/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
ref=dict(N=3,B=3,R=5,Q=9);started=time.monotonic();deadline=started+10;rows=[]
def dist(theta):
 w=E.weights(theta);return statistics.mean(abs(math.log(w[k]/208/ref[k])) for k in 'NBRQ')
old=json.loads((ROOT/'results/dev_aux/task121/controller.json').read_bytes());new=json.loads((ROOT/'results/dev_aux/task124/controller.json').read_bytes())
for seed in (103,104,105):
 rng=random.Random(seed+900000);ds=[[rng.choice((-1,1)) for _ in E.TYPES] for _ in range(6)];initial=E.starts(seed);minimum=float('inf');states=set();hist=[]
 for decisions in itertools.product((0,1,2),repeat=6):
  if time.monotonic()>deadline:raise TimeoutError('10s diagnostic fuse')
  theta=initial[:]
  for a,delta in zip(decisions,ds):
   if a:theta=[max(E.LOW,min(E.HIGH,t+(1 if a==1 else -1)*.4*z)) for t,z in zip(theta,delta)]
  states.add(tuple(E.weights(theta)[k] for k in E.TYPES));minimum=min(minimum,dist(theta))
 actual=[r for r in old['runs'] if r['seed']==seed]+[r for r in new['runs'] if r['seed']==seed]
 distances=[statistics.mean(abs(math.log(r['final_weights'][k]/208/ref[k])) for k in 'NBRQ') for r in actual]
 rows.append(dict(seed=seed,all_schedule_paths=729,distinct_rounded_endpoints=len(states),initial_distance=dist(initial),best_attainable_distance=minimum,actual_final_distances_Task121_then_Task124_runorder=distances,parameter_vectors_not_exported=True))
out=dict(complete=True,scope='Exploratory posthoc optimizer reachability diagnostic; not human-price training',reference=ref,distance='same meanabsolute logratio',rows=rows,all3unconstrained_schedule_paths=2187,fuse_seconds=10,wall_seconds=time.monotonic()-started,limits='Bound assumes any incumbent/plus/minus choice can occur; real reward-selection constraints may restrict these paths. No closest vector is exported, deployed or used for updates. Does not prove optimizer convergence or label adequacy.')
(OUT/'reachability.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))