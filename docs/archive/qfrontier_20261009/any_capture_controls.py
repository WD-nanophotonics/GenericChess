"""Exact finite controls and empirical count-curve sanity audit, not a MC CI."""
from pathlib import Path
from fractions import Fraction as F
from itertools import product
import json,sys,hashlib
root=Path.cwd();sys.path.insert(0,str(root))
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.research_record import write_record
p=Path(__file__).parent;checks=[]
for rho in (F(0),F(1,8),F(1,4),F(3,8),F(1,2),F(1)):
 for kind in ('ray','leaps','cannon'):
  count=F();any_capture=F();mass=F()
  for states in product(range(3),repeat=3):
   weight=F(1);occupied=0;enemy=0
   for i,state in enumerate(states):
    weight*=1-rho if state==0 else rho/2
    occupied|=int(state!=0)<<i;enemy|=int(state==2)<<i
   events=[]
   for target in range(3):
    before=(1<<target)-1
    allowed=not occupied&before if kind=='ray' else True if kind=='leaps' else (occupied&before).bit_count()==1
    if enemy&(1<<target) and allowed:events.append(target)
   count+=weight*len(events);any_capture+=weight*bool(events);mass+=weight
  exact=F(1,2)*(1-(1-rho)**3) if kind=='ray' else 1-(1-rho/2)**3 if kind=='leaps' else F(1,2)*(1-(1-rho)**3-3*rho*(1-rho)**2)
  assert mass==1 and any_capture==exact
  assert count==(3*rho/2 if kind=='leaps' else exact)
  checks.append(dict(density=rho,kind=kind,states=27,count=count,any=any_capture))
probe=json.loads((p/'any-capture-probe.json').read_bytes());report=dict(scope=__doc__,exact_controls=checks,empirical_count_errors=[])
for filename in ('.local_agent/generated6-20261008/coverage.json','.local_agent/generated8-20261008/transfer.json'):
 for case in json.loads(Path(filename).read_bytes())['cases']:
  c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));cfg=EvaluationConfig();_,scope=build_semantic_opportunity_profile(c,cfg)
  r=next(x for x in probe['rules'] if x['seed']==case['seed']);assert r['complete']
  for replicate in r['replicates']:
   errors=[]
   for curve in replicate['curves']:
    i=cfg.density_points.index(curve['density'])
    for t,v in curve['mean'].items():
     sampled_count=F(v['count']);sampled_any=F(v['any']);assert 0<=sampled_any<=sampled_count
     exact_count=scope['types'][t]['curves'][i]['capture'];errors.append(abs(float(sampled_count)-exact_count))
     if curve['density']==0:assert sampled_count==sampled_any==exact_count==0
   report['empirical_count_errors'].append(dict(seed=case['seed'],replicate=replicate['rng_seed'],max_absolute_count_error=max(errors),scope='finite128layout approximation error, no acceptance threshold or confidence interval'))
report['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'any-capture-controls.json',report)
print('Exact controls',len(checks),'max observed MC count error',max(r['max_absolute_count_error'] for r in report['empirical_count_errors']))
