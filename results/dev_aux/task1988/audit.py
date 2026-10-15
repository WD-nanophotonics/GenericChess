"""Independent new-family pooled TRAIN confirmation, no new search."""
from pathlib import Path
from collections import Counter
import json,random,hashlib,itertools
from results.dev_aux.task1980.physical_audit import audit,read,lines
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task1987');OUT=Path('results/dev_aux/task1988')
def interval(ds,seed):
 rng=random.Random(seed);n=len(ds);bs=sorted(sum(ds[rng.randrange(n)] for _ in ds)/n for rep in range(10000));return[bs[250],bs[9749]]
def run():
 physical=audit(ROOT);p=read(ROOT/'run-plan.json');selection=read('results/dev_aux/task1985/selection.json');rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl')
 assert physical['full_study_complete'] and all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_sha'].items())
 prices=selection['confirmation_prices'];cells={(x['family'],x['candidate_side'],x['R'],x['opponent_R']):x for x in rows}
 assert set(cells)==set(itertools.product(range(32),(0,1),prices,(360,720,1440,2880))) and len(cells)==len(rows)
 assert all(x['candidate_proof_nodes']==1024 and x['opponent_nodes']==4096 and x['candidate_cached'] and x['candidate_proof'] for x in rows)
 assert not any(m.get('bank_hit',False) for m in moves)
 profile=None;cleared=False;intents=0
 for e in lines(ROOT/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile
   assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native']
 labels={'UNIT':720,'POOLED':selection['selected_R'],'SEED0':selection['seed_selected_R'][0],'SEED1':selection['seed_selected_R'][1]}
 contrasts=[]
 for label,r in labels.items():
  ds=[sum(cells[f,side,r,opp]['finite_event_score']-cells[f,side,720,opp]['finite_event_score'] for side in (0,1) for opp in (360,720,1440,2880))/8 for f in range(32)]
  u=0 if r==720 else sum((cells[f,s,r,o]['outcome']=='UNKNOWN')+(cells[f,s,720,o]['outcome']=='UNKNOWN') for f in range(32) for s in (0,1) for o in (360,720,1440,2880))/256
  contrasts.append(dict(label=label,R=r,ratio=r/720,mean=sum(ds)/32,family_deltas=ds,bootstrap32family_interval=interval(ds,20261016661988),UNKNOWN_WDL_bounds=[max(-2,sum(ds)/32-u),min(2,sum(ds)/32+u)],per_opponent={o:dict(mean=sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for f in range(32) for s in (0,1))/64,outcomes=dict(Counter(cells[f,s,r,o]['outcome'] for f in range(32) for s in (0,1)))) for o in (360,720,1440,2880)},same_price_cell=r==720))
 coeff=Counter();coeff[labels['POOLED']]+=1;coeff[labels['SEED0']]-=.5;coeff[labels['SEED1']]-=.5
 ds=[sum(weight*cells[f,s,r,o]['finite_event_score'] for r,weight in coeff.items() for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(32)]
 mean=sum(ds)/32;u=sum(abs(weight)*(cells[f,s,r,o]['outcome']=='UNKNOWN') for r,weight in coeff.items() for f in range(32) for s in (0,1) for o in (360,720,1440,2880))/256
 mixture=dict(name='POOLEDminusEQUALTWO16FAMILY_LEARNER_POLICY_MIXTURE',mean=mean,family_deltas=ds,bootstrap32family_interval=interval(ds,20261016661989),UNKNOWN_WDL_bounds=[max(-2,mean-u),min(2,mean+u)],price_coefficients=dict(coeff),scope='Expectation over an equal mixture of two fixed learned policies, evaluated via shared full crossed payoff cells, not two new trainingreplicates or extra physicalgames. Coefficients cancel identical price cells.')
 seen=set()
 for old in ('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json','task1963/cohort0/feasibility.json','task1963/cohort1/feasibility.json','task1967/feasibility.json','task1978/cohort0/feasibility.json','task1978/cohort1/feasibility.json'):
  for r in read(Path('results/dev_aux')/old)['roots']:seen.update(orbit(tuple(r['root'])))
 for r in read('results/dev_aux/task1986/feasibility.json')['roots']:
  assert r['phase']=='DEV';raw=tuple(r['root']);assert raw not in seen;seen.update(orbit(raw))
 result=dict(status='PASS_NEW32FAMILY_CONFIRMATION',physical=physical,labels=labels,contrasts=contrasts,pooled_vs_learner_mixture=mixture,recorded_game_seconds=sum(x['seconds'] for x in rows),outer_late_steps=sum(m['seconds']>=p['step_seconds'] for m in moves),scope='FixedactualH24eventW-L/coldPN1K/UNKNOWNdistinct. Shared32familyclusters acrossmethods/opponents, candidate ratios affect leaf/native/capture. Conditional on these lockedlearners; nohumanfit/fullgenerateddomain/unlimitedWDL/general trainingconvergence claim.')
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],games=physical['games'],moves=physical['moves'],labels=labels,contrasts=[{k:v for k,v in c.items() if k in ('label','ratio','mean','bootstrap32family_interval')} for c in contrasts],mixture={k:v for k,v in mixture.items() if k in ('mean','bootstrap32family_interval')})))
if __name__=='__main__':run()
