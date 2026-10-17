"""Closed full-slot W-L contrasts; no fit or reserve-driven selection."""
from pathlib import Path
from collections import Counter
import json,time
import numpy as np
OUT=Path('results/dev_aux/task2445')
LOW=(.75,0.);HIGH=(1.5,.75)
def load(task):
 f=Path(f'results/dev_aux/task{task}');assert(f/'completion.json').exists();r=lambda name:json.loads((f/name).read_text());return dict(task=task,plan=r('plan.json'),completion=r('completion.json'),slots=r('slots.json'),games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())},decisions=[json.loads(x)for x in(f/'decisions.jsonl').read_text().splitlines()])
def table(panel,price,opponent):
 slots=[s for s in panel['slots']if(s['ratio'],s['hand_ratio'])==price and s['opponent']==opponent];families=sorted(set(s['root']for s in slots));blocks=[];counts=Counter()
 for family in families:
  bounds=[]
  for role in(0,1):
   s,=[s for s in slots if s['root']==family and s['candidate_color']==role];g=panel['games'].get(s['slot']);reward=None if g is None else g['reward'];counts['U'if reward is None else g['outcome']]+=1;bounds.append((-1,1)if reward is None else(reward,reward))
  blocks.append([sum(x[i]for x in bounds)/2 for i in(0,1)])
 return np.asarray(blocks),dict(price=list(price),opponent_R=panel['plan']['opponents'][opponent]['ratio'],counts={k:counts[k]for k in'WLDU'},mean_bounds=np.asarray(blocks).mean(axis=0).tolist())
def difference(high,low,rng):
 lo=high[:,0]-low[:,1];hi=high[:,1]-low[:,0];indices=rng.integers(0,len(lo),size=(10000,len(lo)));return dict(family_bounds=np.stack((lo,hi),axis=1).tolist(),mean_gain_bounds=[float(lo.mean()),float(hi.mean())],descriptive_family_bootstrap=[float(np.quantile(lo[indices].mean(axis=1),.025)),float(np.quantile(hi[indices].mean(axis=1),.975))])
def mechanisms(panel):
 pairs=[];by={s['slot']:[d for d in panel['decisions']if d['slot']==s['slot']]for s in panel['slots']};families=sorted(set(s['root']for s in panel['slots']))
 for opponent in range(len(panel['plan']['opponents'])):
  for family in families:
   for role in(0,1):
    ss=[next(s for s in panel['slots']if s['root']==family and s['candidate_color']==role and s['opponent']==opponent and(s['ratio'],s['hand_ratio'])==p)for p in(LOW,HIGH)];gs=[panel['games'].get(s['slot'])for s in ss]
    if any(g is None for g in gs):pairs.append(dict(family=family,role=role,opponent=opponent,missing=True));continue
    first=None
    for a,b in zip(*(by[s['slot']]for s in ss)):
     if a['choice']==b['choice']:continue
     assert a['root_record']==b['root_record']and a['root_state_sha']==b['root_state_sha'];depths=[None if d['normal_receipt']is None else d['normal_receipt']['completed_depth']for d in(a,b)];matched=all(d['is_candidate']and d['source']=='FULL_SESSION_MATERIAL_SEARCH'and depth==3 for d,depth in zip((a,b),depths));first=dict(ply=a['ply'],is_candidate=a['is_candidate'],sources=[a['source'],b['source']],depths=depths,classification='MATCHED_COMPLETED_D3_PRICE_CHOICE'if matched else'SHARED_ROOT_PROOF_TIMING_OR_CENSOR_NOT_PURE_PRICE',choices=[a['choice'],b['choice']],root_state_sha=a['root_state_sha']);break
    pairs.append(dict(family=family,role=role,opponent=opponent,slots=[s['slot']for s in ss],outcomes=[g['outcome']for g in gs],gain=None if any(g['reward']is None for g in gs)else gs[1]['reward']-gs[0]['reward'],identical_records=gs[0]['record']==gs[1]['record'],first_divergence=first))
 return pairs
def run():
 t=time.perf_counter();rng=np.random.default_rng(852445);panels=[load(task)for task in(2441,2442,2454,2455)];train=panels[0];prices=[tuple(x)for x in json.loads(Path('results/dev_aux/task2441/registration.json').read_text())['train_grid']];train_data={p:table(train,p,0)[0]for p in prices};allstarts=[]
 for initial in prices:
  baseline=train_data[initial].mean(axis=0);eligible=[p for p,a in train_data.items()if a[:,0].mean()>baseline[1]];chosen=min(eligible,key=lambda p:(-train_data[p][:,0].mean(),p))if eligible else initial;allstarts.append(dict(initial=list(initial),closed_table_selector=list(chosen)))
 sections=[];pool=[]
 for panel in panels:
  pp=sorted(set((s['ratio'],s['hand_ratio'])for s in panel['slots']));rows=[];contrasts=[]
  for op in range(len(panel['plan']['opponents'])):
   for price in pp:rows.append(table(panel,price,op)[1])
   if LOW in pp and HIGH in pp:
    h=table(panel,HIGH,op)[0];l=table(panel,LOW,op)[0];contrasts.append(dict(foe_R=panel['plan']['opponents'][op]['ratio'],**difference(h,l,rng)))
    if panel['task']==2455:pool.append((h,l))
  ds=panel['decisions'];depths=Counter((d['is_candidate'],d['normal_receipt']['completed_depth'])for d in ds if d['normal_receipt']is not None);entries=Counter((next(s for s in panel['slots']if s['slot']==d['slot'])['ratio'],next(s for s in panel['slots']if s['slot']==d['slot'])['hand_ratio'])for d in ds if d['is_candidate']and d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'))
  sections.append(dict(task=panel['task'],completion=panel['completion'],rows=rows,commonoffset_contrasts=contrasts,first_divergence_pairs=mechanisms(panel)if LOW in pp and HIGH in pp else[],normal_depths=[dict(candidate=k[0],depth=k[1],count=v)for k,v in depths.items()],candidateverified_entries=[dict(price=list(k),count=v)for k,v in entries.items()],actual_game_seconds=sum(g['seconds']for g in panel['games'].values()),actual_committed_moves=sum(g['plies']for g in panel['games'].values()),saved_certificate_instances=panel['completion']['certificates']))
 pooled=None if not pool else difference(sum(h for h,l in pool)/len(pool),sum(l for h,l in pool)/len(pool),rng);result=dict(status='CLOSED_STRICT_D3_WL_LEARNING_AND_EQUAL_DEPLOYMENT_CONTRAST',primary_selection=json.loads(Path('results/dev_aux/task2444/selection.json').read_text())['selected'],primary_baseline=[1.5,1.5],primary_strict_improvement=False,all6start_closed_table_sensitivity=allstarts,allstarts_is_not_independent_retraining_or_convergence=True,panels=sections,pooled_alt_opponent_commonoffset=pooled,seconds=time.perf_counter()-t,scope='ActualruleW-L only/allplannedslots/Umissing[-1,1]; bothsidesstrictcommittedD3. Primary48TRAINnoimprover/BASEretained; original16BASEreserveisNOTfakezero-gainreplication. Equalcontrastpair(.75,0)vs(1.5,.75) chosenfromTRAINmechanism BEFOREANYreservefitness, thenALL8reservedfamilies/roles/foes2/.5/4 prefrozen. Positivecommonoffsetresultnotuniqueprice/learnedwinnerbeatingoriginalBASE. FixedNboard=Nhand1 ismodelrestrictionbeyondscale; trueWINproofunknownnotLOSS. Descriptivefamilybootstrapnotposteriororpopulationguarantee; firstproof-source divergenceweakenspricecausalinterpretation. No refit/humanfit/defaultadoption.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(selection=result['primary_selection'],panels=[dict(task=r['task'],rows=r['rows'],contrasts=r['commonoffset_contrasts'])for r in sections],pooled=pooled)))
if __name__=='__main__':run()
