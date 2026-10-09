"""Bounded exact colored-event union at two first template sources per rule.
Changed-premise feasibility only:critical2100C/X and2101P/X, no full-table rank
or candidate claim. Include all supported endpoint events at a selected source;
decline above12distinct events (4095intersections), never truncate/zero them.
No new game/task trajectory or label fitting. Check three-cell closed forms first.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from functools import lru_cache
import json,sys,time,hashlib
root=Path.cwd();sys.path[:0]=[str(root),str(root/'.local_agent/finite-law-20261009')]
from finite_law import collect
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from scripts.research_record import write_record
@lru_cache(None)
def joint(events,rho):
 targets=frozenset(e[0] for e in events);clear=frozenset().union(*(e[1] for e in events))
 if targets&clear:return F()
 constraints={(cells-clear-targets,k-len(cells&targets)) for _,_,cells,k in events if k is not None}
 if any(k<0 or k>len(cells) for cells,k in constraints):return F()
 constraints=sorted(constraints,key=lambda x:(sorted(x[0]),x[1]));cells=sorted(frozenset().union(*(c for c,k in constraints)));states={(0,)*len(constraints):F(1)}
 for cell in cells:
  following={}
  for s,weight in states.items():
   following[s]=following.get(s,F())+weight*(1-rho);n=tuple(v+int(cell in c) for v,(c,k) in zip(s,constraints))
   if all(v<=k for v,(c,k) in zip(n,constraints)):following[n]=following.get(n,F())+weight*rho
  states=following
 return (rho/2)**len(targets)*(1-rho)**len(clear)*states.get(tuple(k for c,k in constraints),F())
def union(events,rho):
 events=tuple(sorted(set(events),key=repr))
 if len(events)>12:raise ValueError('more than12event exact feasibility boundary')
 return sum(((-1)**(k+1)*joint(tuple(xs),rho) for k in range(1,len(events)+1) for xs in combinations(events,k)),F())
controls=0
for rho in (F(0),F(1,8),F(1,4),F(3,8),F(1,2),F(1)):
 for kind in ('ray','leaps','cannon'):
  events=[(i,frozenset(range(i)) if kind=='ray' else frozenset(),frozenset(range(i)) if kind=='cannon' else frozenset(),1 if kind=='cannon' else None) for i in range(3)]
  expected=F(1,2)*(1-(1-rho)**3) if kind=='ray' else 1-(1-rho/2)**3 if kind=='leaps' else F(1,2)*(1-(1-rho)**3-3*rho*(1-rho)**2)
  assert union(events,rho)==expected;controls+=1
p=Path(__file__).parent;data=json.loads(Path('.local_agent/generated8-20261008/transfer.json').read_bytes());fact=json.loads((p/'source-saturation-factorial.json').read_bytes());report=dict(scope=__doc__,closed_form_controls=controls,rows=[]);start=time.monotonic()
for seed,types in [(202610082100,('C','X')),(202610082101,('P','X'))]:
 case=next(c for c in data['cases'] if c['seed']==seed);c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));cfg=EvaluationConfig();area=c.board_size**2;tpl=next(r for r in fact['rules'] if r['seed']==seed)['template_sources'];sources=[min(i for i in tpl if i//area==owner) for owner in (0,1)]
 for t in types:
  edges=collect(c,c.ir,t,cfg)[0]['target_enemy']
  for index in sources:
   events=[(target,cl,cells,k) for target,options in edges[index].items() for cl,cells,k in options];row=dict(seed=seed,type=t,owner_source_index=index,events=len(set(events)));report['rows'].append(row)
   try:row['curves']=[dict(density=rho,exact_any=union(events,rho)) for rho in map(lambda x:F(str(x)),cfg.density_points)];row['complete']=True
   except ValueError as exc:row.update(complete=False,unsupported=str(exc))
   assert time.monotonic()-start<30
report['seconds']=time.monotonic()-start;report['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'exact-any-source.json',report);print('controls',controls,'sources',[(r['type'],r['events'],r['complete']) for r in report['rows']],'seconds',report['seconds'])
