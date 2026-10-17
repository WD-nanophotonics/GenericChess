from pathlib import Path
from collections import Counter
import json,time
import numpy as np
from results.dev_aux.task2406.analyze import contrast
OUT=Path('results/dev_aux/task2421')
def run():
 t=time.perf_counter();selected=json.loads(Path('results/dev_aux/task2405/selection.json').read_text())['selected'];rng=np.random.default_rng(842121);data={};rows=[]
 for policy,task in(('ON',2402),('OFF',2420)):
  f=Path(f'results/dev_aux/task{task}');slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())}
  for price in([1.5,1.5],selected):
   blocks=[];counts=Counter();seconds=0.
   for family in range(8):
    bounds=[]
    for role in(0,1):
     s,=[s for s in slots if s['root']==family and s['candidate_color']==role and[s['ratio'],s['hand_ratio']]==price];g=games.get(s['slot']);r=None if g is None else g['reward'];counts['U'if r is None else g['outcome']]+=1;bounds.append((-1,1)if r is None else(r,r));seconds+=0 if g is None else g['seconds']
    blocks.append([sum(x[i]for x in bounds)/2 for i in(0,1)])
   data[(policy,tuple(price))]=np.array(blocks);rows.append(dict(policy=policy,price=price,counts={k:counts[k]for k in'WLDU'},actual_game_seconds=seconds))
 base=(1.5,1.5);sel=tuple(selected);solver=[dict(price=list(p),ONminusOFF=contrast(data[('ON',p)],data[('OFF',p)],rng))for p in(base,sel)];prices=[dict(policy=a,selected_minus_BASE=contrast(data[(a,sel)],data[(a,base)],rng))for a in('ON','OFF')]
 # Interval-difference preserves UNKNOWN in all four factorial cells.
 a=data[('ON',sel)];b=data[('ON',base)];c=data[('OFF',sel)];d=data[('OFF',base)];low=a[:,0]-b[:,1]-c[:,1]+d[:,0];high=a[:,1]-b[:,0]-c[:,0]+d[:,1];idx=rng.integers(0,8,size=(10000,8));interaction=dict(family_bounds=np.stack([low,high],axis=1).tolist(),mean_bounds=[float(low.mean()),float(high.mean())],descriptive_cluster_bootstrap_envelope=[float(np.quantile(low[idx].mean(axis=1),.025)),float(np.quantile(high[idx].mean(axis=1),.975))])
 result=dict(status='CLOSED_FIXED_OPPONENT_TWO_BY_TWO_PRICE_AND_CANDIDATE_PROOF',rows=rows,solver_effects_fixed_price=solver,price_effects_fixed_solver=prices,interaction=interaction,seconds=time.perf_counter()-t,scope='FIXED SAMEfoe2/playerbudgets, onlycandidateproofON/OFF. ALL32ONalreadyqualified2402 reusedwithoutduplication,32OFFnew; rootsnowexposed/post-fitmechanismnotconfirmation. Samephase/callerCEILINGS, OFFunusedproofbudgetnotreallocated; NOTequalspentcostorbestextra-normal-searchcomparison. U/missingintervals preserved. Paired8familybootstrapdescriptive; nohuman/quantityreward/refit/default/PRIMARYadoption.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
