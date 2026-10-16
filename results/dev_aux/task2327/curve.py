"""Exposed-TRAIN engineering budget curve, not a new validation set."""
from pathlib import Path
from collections import Counter
import json,time,numpy as np
OUT=Path('results/dev_aux/task2327')
def run():
 t=time.perf_counter();read=lambda p:json.loads(Path(p).read_text());tasks={8:2307,12:2325,60:2313};games={};summary={};plans={};key=lambda g:(g['root'],g['ratio'],g['candidate_color'])
 assert read('results/dev_aux/task2326/task2325-audit.json')['status']=='PASS_FULL_ACTUAL_RECORDS_PHASES_CERTIFICATES_SINGLEAXIS_CONTRACT'
 for budget,task in tasks.items():
  f=Path(f'results/dev_aux/task{task}');p=read(f/'plan.json');done=read(f/'completion.json');plans[budget]=p;rows=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));games[budget]={key(g):g for g in rows};summary[str(budget)]=dict(actual_games=len(rows),planned_slots=32,outcomes=dict(Counter(g['outcome']for g in rows)),unknown=sum(g['reward']is None for g in rows),actual_game_seconds=sum(g['seconds']for g in rows),candidate_proof_budget=p['candidate']['proof_seconds'],shared_verification_budget=p['candidate']['verification_seconds'],prices={str(price):dict(Counter(g['outcome']for g in rows if g['ratio']==price))for price in(1.,2.)})
 for p in plans.values():
  q=plans[8];assert p['H']==q['H']and p['opponents']==q['opponents']and p['step_seconds']==q['step_seconds'];assert Path(p['input']).read_bytes()==Path(q['input']).read_bytes();assert all(p['candidate'][k]==q['candidate'][k]for k in q['candidate']if k not in('proof_seconds','verification_seconds'))
 roots=sorted({k[0]for k in games[8]});rng=np.random.default_rng(20261017802327);contrasts={};pairs=[]
 def reward(b,k):
  g=games[b].get(k);return(-1.,1.)if g is None or g['reward']is None else(g['reward'],)*2
 for a,b in((8,12),(12,60),(8,60)):
  for price in(1.,2.):
   ff=[]
   for f in roots:
    vv=[]
    for role in(0,1):
     k=(f,price,role);al,ah=reward(a,k);bl,bh=reward(b,k);vv.append((bl-ah,bh-al));x=games[a].get(k);y=games[b].get(k);pairs.append(dict(low_budget=a,high_budget=b,key=k,actual_rewards=[None if x is None else x['reward'],None if y is None else y['reward']],identical_actual_record=None if x is None or y is None else x['record']==y['record']))
    ff.append((sum(z[0]for z in vv)/2,sum(z[1]for z in vv)/2))
   lo=np.array([z[0]for z in ff]);hi=np.array([z[1]for z in ff]);i=rng.integers(0,8,size=(10000,8));contrasts[f'{b}-minus-{a}:price{price}']=dict(lower=float(lo.mean()),upper=float(hi.mean()),family_blocks=8,descriptive95_envelope=[float(np.quantile(lo[i].mean(axis=1),.025)),float(np.quantile(hi[i].mean(axis=1),.975))],per_family=ff)
 out=dict(status='PASS_EXPOSED_TRAIN_LOW_BUDGET_CURVE',budgets=summary,paired_contrasts=contrasts,actual_record_pairs=pairs,new_games=len(games[12]),reused_game_slots=len(games[8])+len(games[60]),seconds=time.perf_counter()-t,scope='Budget12selectedusingexposedLOW60paidconversioncost; SAMEALL8families/roles/prices/foe/LOWtrigger. New32LOW12games versusreusedLOW8/LOW60; not96newgames orindependentvalidation. FiniteW-L/U only; missingbounds/8familyclusters. No pricefit/DEV/defaultadoption, no equivalence/stability/optimalbudgetclaim.')
 with(OUT/'result.json').open('x')as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items()if k not in('actual_record_pairs','paired_contrasts')}))
if __name__=='__main__':run()
