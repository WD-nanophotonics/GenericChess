from pathlib import Path
from math import isclose
import json
T=Path('results/dev_aux/task2534');O=Path('results/dev_aux/task2536')
def run():
 first={}
 for line in(T/'episodes.jsonl').read_bytes().rsplit(b'\n',1)[0].splitlines():
  e=json.loads(line)
  if e['game']==0:first[e['generator_seed'],e['seed'],e['method']]=e
 qq={}
 for line in(T/'queries.jsonl').read_bytes().rsplit(b'\n',1)[0].splitlines():
  q=json.loads(line)
  if q['game']==0:qq.setdefault((q['generator_seed'],q['seed'],q['method']),[]).append(q)
 p=json.loads((T/'registration.json').read_text());rows=[]
 for gs in p['generator_seeds']:
  for seed in p['initial_seeds']:
   k=gs,seed;a=first.get(k+('fixed5',));b=first.get(k+('free6',))
   if a is None or b is None:continue
   for field in('initial_weights','initial_record','record','outcome','nodes','queries','ending'):assert a[field]==b[field],(k,field)
   assert all(isclose(x,y,rel_tol=1e-12,abs_tol=1e-14)for x,y in zip(a['weights'][1:],b['weights'][1:]));assert a['weights'][0]==1.
   aa=qq.get(k+('fixed5',),[]);bb=qq.get(k+('free6',),[]);assert len(aa)==len(bb)==a['queries']
   for x,y in zip(aa,bb):
    for field in('record_before','record_after','features','weights','complete','value','pv_phi','pv_terminal','prediction','nodes','reason'):assert x[field]==y[field],(k,field)
    if x['complete']:assert x['gradient'][0]==0 and x['gradient'][1:]==y['gradient'][1:]
   rows.append(dict(rule=gs,seed=seed,queries=len(aa),nodes=a['nodes'],outcome=a['outcome'],fixed_P=a['weights'][0],free_P=b['weights'][0],same_other5=True))
 result=dict(status='PASS_RETURNED_FIRST_EPISODE_COMMON_SEARCH_AND_CREDIT',expected=16,actual=len(rows),missing=16-len(rows),rows=rows,scope='Firstgame perrule/seed fixedbeforeoutcomes; SAME rawinitial/prefix/order/actions/PV/nodecounts/outcome. OnlyPcreditmaskedinfixed5, other5updatesidentical. No claim laterpolicies/episodecountsidentical, noactualstrengthproof.')
 (O/'pairing-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
