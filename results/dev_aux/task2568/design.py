"""Frozen input/source/model binding and total-cost accounting, no newfitness."""
from pathlib import Path
import json,hashlib,itertools,datetime,sys

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run():
 root=Path('results/dev_aux/task2568');reg=json.loads((root/'registration.json').read_text());p=json.loads((root/'plan.json').read_text());started=json.loads((root/'started.json').read_text());t=json.loads((root/'result.json').read_text())
 for name,h in reg['plans'].items():assert sha(root/name)==h
 for name,h in p['pins'].items():assert sha(name)==h,name
 assert started['plan_sha']==sha(root/'plan.json')and started['utc']>=reg['registered_at'];expected=set(itertools.product([1977,8173,27182,31415],['TD','TC','WDL']));actual={(a['seed'],a['method'])for a in t['arms']};assert actual<=expected and len(actual)==len(t['arms']);nodecost=t['nodes'];wall=t['seconds'];counts={'TRAIN_nodes':t['nodes'],'TRAIN_seconds':t['seconds']};panels={}
 for task,slots,families,foes in[(2568,512,list(range(421001,421009)),['uniform','random99031']),(2570,256,list(range(431001,431005)),['uniform_nonpawn2','lograndom65537'])]:
  d=Path('results/dev_aux/task'+str(task));ep=json.loads((d/'eval-plan.json').read_text());er=json.loads((d/'eval-result.json').read_text());binding=json.loads((d/'eval-binding.json').read_text());st=json.loads((d/'eval-started.json').read_text());assert binding['training_sha']==sha(root/'result.json')and binding['plan_sha']==sha(d/'eval-plan.json');assert ep['session_id']==p['session_id'];assert st['utc']>ep['registered_at'];cartesian=set(itertools.product([0],[1977,8173,27182,31415],families,[0,1],['initial','TD','TC','WDL'],foes));assert len(ep['slots'])==slots and set(map(tuple,ep['slots']))==cartesian
  if task==2570:
   tr=json.loads((d/'registration.json').read_text())
   for n,h in tr['pins'].items():assert sha(d/n)==h,n
   assert tr['registered_at']<json.loads((root/'eval-started.json').read_text())['utc'];assert sha(d/'result.json')==sha(root/'result.json')and sha(d/'plan.json')==sha(root/'plan.json')
  records={tuple(g['slot']):g for g in map(json.loads,(d/'eval-games.jsonl').open())};controls=0;unresolved_controls=0
  for slot,game in records.items():
   gs,seed,family,color,method,foe=slot
   if method=='initial':continue
   a=next(a for a in t['arms']if a['seed']==seed and a['method']==method)
   if a['weights']!=a['initial']:continue
   baseline=records.get((gs,seed,family,color,'initial',foe))
   if baseline is None or game['outcome']is None or baseline['outcome']is None:unresolved_controls+=1;continue
   assert game['record']==baseline['record']and game['reward']==baseline['reward']and game['nodes']==baseline['nodes']and game['queries']==baseline['queries'];controls+=1
  endpoints={tuple((a['seed'],a['method'])):a for a in binding['all_models']};assert set(endpoints)==actual
  for a in t['arms']:assert endpoints[a['seed'],a['method']]==a
  nodecost+=er['nodes'];wall+=er['seconds'];counts[str(task)+'_EVAL_nodes']=er['nodes'];counts[str(task)+'_EVAL_seconds']=er['seconds'];panels[str(task)]=dict(planned=slots,executed=er['actual'],actual_terminal=er['actual_terminal'],unknown=er['unknown'],missing=er['missing'],complete_unchanged_model_controls=controls,unresolved_unchanged_model_controls=unresolved_controls)
 result=dict(status='PASS_ALL_FROZEN_INPUTS_SOURCE_AND_ENDPOINT_BINDINGS',panels=panels,source_pins=len(p['pins']),all_expected_training_arms=len(expected),actual_training_arms=len(actual),producer_nodes=nodecost,listed_producer_seconds=wall,components=counts,scope='All threeproducerphases paidonce, includingopponent/baseline/proposal/failed searches. TRAIN result reused fortransfer, NOTchargedtwice. Auditnodes/engineering/I-O/transportadditional. AllCartesianinputs/clock/pins beforeEVAL; no DEVselection/oldcaps extension.')
 (root/'design-costs.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
