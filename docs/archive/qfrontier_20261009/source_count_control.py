"""Analytical endpoint-count controls for the shared-layout source factorial.
Uses existing finite Bernoulli path-union evaluator, numeric floats (not a new
rational certificate). Source policy changes only the averaging weights. No
formula fitting; report Monte Carlo order discrepancies rather than hide them.
"""
from pathlib import Path
import sys,json,hashlib
root=Path.cwd();sys.path[:0]=[str(root),str(root/'.local_agent/finite-law-20261009')]
from finite_law import collect
from generic_chess.ai.evaluation.semantic import _path_union
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.research_record import write_record
p=Path(__file__).parent;fact=json.loads((p/'source-saturation-factorial.json').read_bytes());report=dict(scope=__doc__,rules=[])
for filename in ('.local_agent/generated6-20261008/coverage.json','.local_agent/generated8-20261008/transfer.json'):
 for case in json.loads(Path(filename).read_bytes())['cases']:
  c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));cfg=EvaluationConfig();r=next(x for x in fact['rules'] if x['seed']==case['seed']);assert r['complete'];values={}
  for t in r['replicates'][0]['methods']['uniform_count']['values']:
   edges=collect(c,c.ir,t,cfg)[0]['target_enemy'];values[t]={}
   for name,indices in [('uniform',range(len(edges))),('template',r['template_sources'])]:
    values[t][name]=sum(w*sum(_path_union(events,rho)*rho/2 for i in indices for events in edges[i].values())/len(indices) for rho,w in zip(cfg.density_points,cfg.density_weights))
  orders={name:sorted(values,key=lambda t:(-values[t][name],t)) for name in ('uniform','template')}
  mismatches=[dict(seed=rep['seed'],method=name+'_count',sample_order=rep['methods'][name+'_count']['order'],analytical_order=orders[name]) for rep in r['replicates'] for name in orders if rep['methods'][name+'_count']['order']!=orders[name]]
  row=dict(seed=case['seed'],analytical_values=values,analytical_orders=orders,mc_order_discrepancies=mismatches);report['rules'].append(row);print(case['seed'],'mismatches',len(mismatches),orders,flush=True)
report['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'source-count-control.json',report)
