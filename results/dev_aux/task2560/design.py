"""Independent exact registration/model/slot binding and total physical cost audit."""
from pathlib import Path
from collections import Counter
import json,hashlib,random,itertools
R=Path('results/dev_aux');T=R/'task2558';E=R/'task2559';A=R/'task2560'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 reg=load(T/'study-registration.json');tp=load(T/'plan.json');ep=load(E/'plan.json');old=load(E/'registered-plan-before-binding.json');assert sha(E/'registered-plan-before-binding.json')==reg['pins']['results/dev_aux/task2559/plan.json']
 for n,h in reg['pins'].items():
  if n=='results/dev_aux/task2559/plan.json':continue
  assert sha(Path(n))==h,n
 copy=dict(ep);copy['pins']={};assert copy==old
 assert sha(T/'plan.json')==load(T/'started.json')['plan_sha'];assert sha(E/'plan.json')==load(E/'started.json')['plan_sha']==load(E/'pre-fitness-binding.json')['plan_sha']
 tr=load(T/'result.json');mo=load(E/'models.json');assert mo['arms']==tr['arms'];assert mo['expected_arms']==32
 keys={(g,m,s)for g in tp['generator_seeds']for m,s in tp['arms_order']};got={(a['generator_seed'],a['method'],a['seed'])for a in mo['arms']};assert got<=keys and len(got)==len(mo['arms'])
 if tr['status']=='COMPLETE':assert got==keys and all(a['nodes']==tp['nodes_per_arm']for a in mo['arms'])
 for a in mo['arms']:
  rng=random.Random(a['seed']);assert a['initial']==[1.]+[rng.uniform(.5,1.5)for _ in range(5)]
 expected=set(itertools.product(tp['generator_seeds'],tp['initial_seeds'],ep['families'],[0,1],['initial','Mean','CostClock'],ep['opponents'],[3]));assert len(ep['slots'])==len(set(map(tuple,ep['slots'])))==len(expected)==384 and set(map(tuple,ep['slots']))==expected
 train=Counter();eval=Counter()
 for D,c in [(T,train),(E,eval)]:
  for line in(D/'queries.jsonl').open():
   q=json.loads(line);c['nodes']+=q['nodes'];c['queries']+=1;c['failed_queries']+=not q['complete'];c['failed_nodes']+=q['nodes']if not q['complete']else 0;c['search_seconds']+=q['seconds'];c['candidate_nodes'if q['actor']==q.get('color',q.get('slot',[0,0,0,None])[3])else'foe_nodes']+=q['nodes']
  rr=load(D/'result.json');assert c['nodes']==rr['nodes'];c['listed_producer_wall_seconds']=rr['seconds']
  for line in(D/'games.jsonl').open():
   g=json.loads(line);c['physical_games']+=1;c['actual_terminal']+=g['outcome']is not None;c['unknown']+=g['outcome']is None
 total=Counter(train);total.update(eval)
 out=dict(status='PASS_EXACT_PREFITNESS_BINDING_ALL_MODELS_SLOTS_AND_RECOUNTED_COSTS',all_planned_arms=32,available_arms=len(got),all_planned_slots=384,training=dict(train),evaluation=dict(eval),total=dict(total),scope='All paid candidate/foe/baseline/incomplete searches charged; audits/engineering/plotting/delivery/token overhead additional, not equal CPU. Missing and U retained; no frozen cap extension or root/model selection.')
 (A/'design-costs.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
