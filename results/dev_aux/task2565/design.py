"""Snapshot nonleakage, complete Cartesian slot/model/cost binding and fixed plans."""
from pathlib import Path
import json,hashlib,itertools,datetime
D=Path('results/dev_aux/task2565')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 frozen=json.loads((D/'frozen-eval-plan-hashes.json').read_text());cut=datetime.datetime.fromisoformat(frozen['at']);counts={};allgames={}
 for name,h in frozen['sha256'].items():assert sha(name)==h,name
 for domain in ['chess','generic']:
  d=D/domain;p=json.loads((d/'plan.json').read_text());t=json.loads((d/'result.json').read_text());gs=[json.loads(l)for l in(d/'games.jsonl').open()];allgames[domain]=gs;declared=[tuple(a)for a in p['arms_order']];actual=[(a['generator_seed'],a['seed'],a['method'])for a in t['arms']];assert len(declared)==len(set(declared))and len(actual)==len(set(actual))and actual==declared[:len(actual)]
  assert t['nodes']==sum(a['nodes']for a in t['arms'])==sum(g['nodes']for g in gs)
  for a in t['arms']:
   gg=[g for g in gs if(g['generator_seed'],g['seed'],g['method'])==(a['generator_seed'],a['seed'],a['method'])];assert a['nodes']<=p['nodes_per_arm'];expected=[]
   for b in p['snapshot_nodes']:
    candidates=[g for g in gg if g['total_nodes']<=b]
    if candidates:
     g=max(candidates,key=lambda g:g['index']);expected.append(dict(boundary=b,nodes=g['total_nodes'],index=g['index'],weights=g['weights']))
   assert expected==a['snapshots'];assert gg[-1]['weights']==a['weights']
  ep=json.loads((d/'eval-plan.json').read_text());binding=json.loads((d/'eval-binding.json').read_text());start=json.loads((d/'eval-started.json').read_text());assert cut<datetime.datetime.fromisoformat(start['utc']);assert binding['training_sha']==sha(d/'result.json')and binding['plan_sha']==sha(d/'eval-plan.json')and binding['all_models']==t['arms']
  families=sorted({s[2]for s in ep['slots']});rules=sorted({x[0]for x in p['arms_order']});expected=set(itertools.product(rules,p['initial_seeds'],families,[0,1],['initial']+p['methods'],ep['foes']));assert set(map(tuple,ep['slots']))==expected and len(ep['slots'])==len(expected);counts[domain]=dict(registered_arms=len(declared),returned_arms=len(actual),missing_arms=len(declared)-len(actual),registered_slots=len(expected),snapshot_audits=sum(len(a['snapshots'])for a in t['arms']),train_nodes=t['nodes'])
 d=D/'chess-curve';r=json.loads((d/'result.json').read_text());assert r['source_sha']==sha(D/'chess/result.json')and r['additional_training_nodes']==0;orig=json.loads((D/'chess/result.json').read_text());mapped={(a['generator_seed'],a['seed'],a['method']):a for a in orig['arms']}
 for a in r['arms']:
  old=mapped[0,a['seed'],a['original_method']];gg=[g for g in allgames['chess']if g['seed']==a['seed']and g['method']==a['original_method']and g['total_nodes']<=a['nominal_boundary']]
  if gg:
   last=max(gg,key=lambda g:g['index']);assert a['nodes']==last['total_nodes']and a['weights']==last['weights']and a['source_episode']==last['index']
  else:assert a['nodes']==0 and a['weights']==old['initial']and a['source_episode']==-1
  assert a['method']==a['original_method']+'@'+str(a['nominal_boundary'])
 ep=json.loads((d/'eval-plan.json').read_text());expected=set(itertools.product([0],[1977,8173,27182,31415],[321001,321002],[0,1],[m+'@'+str(b)for m in ['Fixed','SelfCandidate','SelfEvery']for b in [25000,50000,75000]],ep['foes']));assert len(expected)==288 and set(map(tuple,ep['slots']))==expected
 assert cut<datetime.datetime.fromisoformat(json.loads((d/'eval-started.json').read_text())['utc']);assert len(r['arms'])==36
 source=json.loads((D/'source-review-before-fitness.json').read_text())
 for n,h in source['files'].items():assert sha(n)==h,n
 out=dict(status='PASS_ALL_SNAPSHOTS_AND_PRE_FITNESS_BINDINGS',domains=counts,curve_models=36,curve_slots=288,all_pre_fitness_plan_hashes=True,source_inventory_unchanged=len(source['files']),scope='All planned slots and absentmodels retained, ALL snapshots are last closedepisode <=boundary. Originalcaps/fixedfoes/source preserved, no postfitnessselection or oldcap extension. Equal searchnodes only: prefix/replay/engineering paidwall/explicit work separately.')
 (D/'design-costs.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
