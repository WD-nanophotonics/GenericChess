"""Retrospective all-initial diagnostics; no new price choice or game."""
from pathlib import Path
from collections import Counter,defaultdict
import json,random,hashlib
OUT=Path('results/dev_aux/task1853')
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 outputs=[]
 for task in (1825,1848):
  folder=Path(f'results/dev_aux/task{task}');rows=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()];idx={(x['phase'],x['family'],x['candidate_side'],x['candidate_proof'],x['R']):x for x in rows};selection=load(folder/'selection-before-dev.json');prices=(360,720,1440)
  for proof in (False,True):
   selected=selection['selections'][str(proof)]['selected'];train=[]
   for family in range(16):train.append({r:sum(idx[('TRAIN',family,side,proof,r)]['finite_event_score'] for side in (0,1)) for r in prices})
   def select(vectors):
    net={r:sum(v[r] for v in vectors) for r in prices};return min(prices,key=lambda r:(-net[r],r))
   assert select(train)==selected
   rng=random.Random(2026101560);boot=Counter();all_converge=flat=0
   for _ in range(20000):
    sampled=rng.choices(train,k=16);net={r:sum(v[r] for v in sampled) for r in prices};boot[select(sampled)]+=1;flat+=len(set(net.values()))==1
    endpoints=[]
    for initial in prices:
     current=initial
     while True:
      candidates=[r for r in prices if abs(prices.index(r)-prices.index(current))==1 and net[r]>net[current]]
      if not candidates:break
      current=min(candidates,key=lambda r:(-net[r],r))
     endpoints.append(current)
    all_converge+=len(set(endpoints))==1
   contrasts=[]
   for initial in prices:
    fam=[];transitions=Counter();role=defaultdict(list)
    for family in range(16,32):
     vals=[]
     for side in (0,1):
      a=idx[('DEV',family,side,proof,initial)];b=idx[('DEV',family,side,proof,selected)];d=b['finite_event_score']-a['finite_event_score'];vals.append(d);role[side].append(d);transitions[a['outcome']+'->'+b['outcome']]+=1
     fam.append(sum(vals)/2)
    rng=random.Random(2026101560);bs=sorted(sum(rng.choices(fam,k=16))/16 for _ in range(20000))
    contrasts.append(dict(initial=initial,learned=selected,identical_cell=initial==selected,mean=sum(fam)/16,family95=[bs[500],bs[19499]],role_means={k:sum(v)/len(v) for k,v in role.items()},transitions=dict(transitions)))
   outputs.append(dict(task=task,proof=proof,selected=selected,nonflat_train_families=sum(len(set(v.values()))>1 for v in train),train_leave_one_family_out_selections=dict(Counter(select(train[:i]+train[i+1:]) for i in range(16))),train_bootstrap20000_selection_counts=dict(boot),train_bootstrap_all_three_strict_paths_converge=all_converge,train_bootstrap_flat=flat,all_initial_DEV=contrasts))
 prior=[]
 for task in (1791,1792):
  r=load(f'results/dev_aux/task{task}/role_report.json')
  good=[x for x in r['DEV_contrasts'] if x['role']=='BALANCED' and x['contrast']=='price_with_solver' and x['opponent'] in ('UNIT64','UNIT4096')]
  prior.append(dict(task=task,contrast='BtoD only: fixed opponent within proofenabledpricepair; legacy AtoB jointly changes opponents and is excluded',strata=good))
 evidence={f:sha(f) for f in ['results/dev_aux/task1825/games.jsonl','results/dev_aux/task1848/games.jsonl','results/dev_aux/task1791/role_report.json','results/dev_aux/task1792/role_report.json',str(Path(__file__).relative_to(Path.cwd()))]}
 result=dict(status='COMPLETE_RETROSPECTIVE_DIAGNOSTIC',scope='All3previouslydeclared initial grid prices shown, no cherry-picked initial or fresh validation claim. TRAIN bootstrap describes exposed TRAIN sample only, not calibrated generalization; changing root law AND allocation prevents causal attribution of1825vs1848pricechanges.',results=outputs,prior_opponent_review=prior,decision='Do not start an opponent-strength cohort merely assuming stronger opposition always improves price signal:1791and1792 stratum differences reverse direction. Current384quarter-to-phase comparison changes roots too. Need a smaller mechanism/identifiability check before more unchanged games.',source_sha=evidence,new_go_or_games=0)
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(all_initial=[dict(task=x['task'],proof=x['proof'],selected=x['selected'],DEV=[{k:y[k] for k in ('initial','mean','family95')} for y in x['all_initial_DEV']],bootstrap=x['train_bootstrap20000_selection_counts']) for x in outputs],opponents=prior)))
if __name__=='__main__':run()
