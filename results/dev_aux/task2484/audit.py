
"""Independent interval coverage/co-optimal action check of persisted finite-tree line models."""
from pathlib import Path
from fractions import Fraction as F
from math import inf,isclose
from copy import deepcopy
import json,time
from results.dev_aux.task2467.margin import compute as float2
from results.dev_aux.task2469.margin import compute as float3
OUT=Path('results/dev_aux/task2484')
def check(panel,model):
 folder=Path(f"results/dev_aux/task{panel['task']}");nodes=[json.loads(x)for x in(folder/'nodes.jsonl').read_text().splitlines()]
 base=list(map(lambda v:F(str(v)),panel['base']));direc=list(map(F,panel['direction']));lo,hi=map(lambda v:F(str(v)),panel['domain'])
 lines=set((F(n['features'][-1])+sum(F(x)*v for x,v in zip(n['features'],base)),sum(F(x)*v for x,v in zip(n['features'],direc)))for n in nodes if n['status']=='ongoing')
 expected={lo,hi}
 for a,b in lines:
  for c,d in lines:
   if b!=d and lo<(c-a)/(b-d)<hi:expected.add((c-a)/(b-d))
 cuts=list(map(F,model['cuts']));assert cuts==sorted(expected)
 vs=[r for r in model['pieces']if r['kind']=='vertex'];ss=[r for r in model['pieces']if r['kind']=='open_interval']
 assert sorted(F(r['q'])for r in vs)==cuts
 assert sorted((F(r['lo']),F(r['hi']))for r in ss)==list(zip(cuts,cuts[1:]))
 checks=0
 for row in model['pieces']:
  q=F(row['q']);point=[float(a+d*q)for a,d in zip(base,direc)];r=(float2 if len(base)==2 else float3)(nodes,point,3)
  best=max(a['score']for a in r['all_choices']);winners=[i for i,a in enumerate(r['all_choices'])if isclose(a['score'],best,rel_tol=0,abs_tol=1e-12)]
  assert row['cooptimal']==winners and row['chosen']==winners[0]
  assert len(row['actions'])==len(r['all_choices'])
  for saved,actual in zip(row['actions'],r['all_choices']):
   assert saved['choice']==actual['choice']and saved['features']==actual['features']
   assert isclose(float(F(saved['value'])),actual['score'],rel_tol=0,abs_tol=1e-10)
  checks+=len(r['all_choices'])
 return checks
def run():
 t=time.perf_counter();p=json.loads(Path('results/dev_aux/task2473/plan.json').read_text());models=json.loads(Path('results/dev_aux/task2473/result.json').read_text())['panels'];checks=sum(check(panel,model)for panel,model in zip(p['panels'],models));controls=[]
 for mutation in ('missing_vertex','missing_tied_action'):
  bad=deepcopy(models[1])
  if mutation=='missing_vertex':bad['pieces']=[r for r in bad['pieces']if not(r['kind']=='vertex'and r['q']=='2')]
  else:
   row=next(r for r in bad['pieces']if r['kind']=='vertex'and r['q']=='2');row['cooptimal']=row['cooptimal'][:1]
  try:check(p['panels'][1],bad)
  except AssertionError:controls.append(mutation)
  else:raise AssertionError('unrejected '+mutation)
 r=dict(status='PASS_COMPLETE_INTERVALS_ALL_COOPTIMAL_ACTIONS_AND_NEGATIVE_CONTROLS',root_action_value_checks=checks,rejected=controls,seconds=time.perf_counter()-t,scope='Independentcoverage/allleaf-crossingclosure/allcooptimalrootactions usingalreadyCore-verifiedfiniteD3trees. Exactcutcoverage plusbinaryfloatingfold consistencyatrepresentatives; NOallIEEEequivalence/WDLlabel/uniquetrueprices. q2 isearliertie, notstrictNpreference.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
