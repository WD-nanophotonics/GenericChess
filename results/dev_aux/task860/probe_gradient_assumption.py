import json,sys,time,os,re,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task866';O.mkdir(exist_ok=False)
for n in [360,364,381,509,860]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
from dual_engine import DualEngine
A.EXE=R/'.local_agent/dualprice38/dual.exe';base=[json.loads(l) for l in (R/'results/dev_aux/task838/queries.jsonl').open(encoding='utf-8') if json.loads(l)['mode']=='original'];assert len(base)==32
plan=dict(status='FROZEN_BEFORE_ANY224_NEW_QUERIES',question='Is stableprintedPV enoughforlocalleafprice derivatives when nativeprice tables areheldfixed?',inputs='All32original838fixedcoldpositions/budgets, ownqualifieddualpriceengine',axes=[3,5,6],delta=16,queries=224,selection='Lastunboundedcp line, allbase/plus/minus mustsameprintedPV+depth+bestmove; compare actualscoreincrement against exacttruncated100/90 material-PV increments. Allmissing/bound/mate/changedpaths retained andnotqualified.',scope='Finitecounterexample test ofa sufficientassumption, NOTinfinitesimalgradient/fullTDLeafcertificate. +/-16finitepriceperturb, fixednativeotherconsumers butsearchtree/history maychange. No fit/humanfitness/c69change.',limit_seconds=300)
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');records=[];start=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as j:
 for ci,c in enumerate(base):
  for axis,sign in [(0,0)]+[(a,s) for a in plan['axes'] for s in [-1,1]]:
   assert time.monotonic()-start<300;leaf=list(c['weights'])
   if axis:leaf[axis]+=sign*16
   e=DualEngine(c['weights'],leaf,None,'cold_per_query')
   try:q=e.search(c['initial_sfen'],c['history'],c['nodes_limit']);q.update(case_index=ci,axis=axis,sign=sign);j.write(json.dumps(q)+'\n');j.flush();os.fsync(j.fileno());records.append(q)
   finally:e.close()
(O/'result.json').write_text(json.dumps(dict(status='ALL224_LEAF_PRICE_SENSITIVITY_QUERIES_CLOSED',actual_go=len(records),seconds=time.monotonic()-start),indent=2),encoding='utf-8');print('SENSITIVITY',len(records),round(time.monotonic()-start,3))
