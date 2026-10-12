import json,itertools,time,math,hashlib,datetime
from fractions import Fraction
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task249';D=json.loads((O/'declaration.json').read_bytes());P=R/'results/dev_aux/task242/features.json';assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_features_sha256'];F=json.loads(P.read_bytes());source=json.loads((R/'results/dev_aux/task242/result.json').read_bytes());assert not (O/'result.json').exists();start=time.monotonic();ratios=list(itertools.product(D['grid'],repeat=4));W=np.array([[208]+[round(208*x) for x in t] for t in ratios],dtype=np.int64);results=[];groups={}
for row in F['rows']:groups.setdefault(row['root'],[]).append(row)
for old in source['root_policies']:
 rows=groups[old['root']];numerators=[];denominators=[];goals=[]
 for r in rows:
  branch=[]
  for z in r['branches']:branch.append(W@np.array(z['features'],dtype=np.int64) if 'features' in z else np.full(625,z['terminal'],dtype=np.int64))
  numerators.append(np.sum(branch,axis=0));denominators.append(len(branch));goals.append(Fraction(r['goal']))
 nums=np.array(numerators);dens=np.array(denominators,dtype=np.int64);chosen=np.zeros(625,dtype=np.int64)
 for i in range(1,len(rows)):
  col=np.arange(625);better=nums[i]*dens[chosen]>nums[chosen,col]*dens[i];chosen[better]=i
 ties=nums*dens[chosen]==nums[chosen,np.arange(625)]*dens[:,None];g=[goals[i] for i in chosen];tieMin=[min(goals[i] for i in np.where(ties[:,j])[0]) for j in range(625)];tieMax=[max(goals[i] for i in np.where(ties[:,j])[0]) for j in range(625)];results.append(dict(root=old['root'],phase=old['phase'],chosen_indices=chosen.tolist(),goal_values=[str(x) for x in g],tie_goal_min=[str(x) for x in tieMin],tie_goal_max=[str(x) for x in tieMax],exact_goal_optimum=str(max(goals)),backprop_numerators=nums.tolist(),backprop_denominators=dens.tolist()))
train=[r for r in results if r['phase']=='train'];held=[r for r in results if r['phase']=='heldout'];means=[sum(Fraction(r['goal_values'][j]) for r in train)/len(train) for j in range(625)];best=max(means);optimal=[j for j,v in enumerate(means) if v==best];selected=min(optimal,key=lambda j:(sum(math.log(v)**2 for v in ratios[j]),ratios[j]));endpoint=dict(selected=selected,ratios=dict(zip('NBRQ',ratios[selected])),train=str(means[selected]),train_optima=len(optimal),frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat());(O/'endpoint.json').write_text(json.dumps(endpoint,indent=2),encoding='utf-8');heldmeans=[sum(Fraction(r['goal_values'][j]) for r in held)/len(held) for j in range(625)];models=[dict(index=j,ratios=dict(zip('NBRQ',v)),train=str(means[j]),heldout=str(heldmeans[j])) for j,v in enumerate(ratios)];bounds=[];unit=312
for phase in ('train','heldout'):
 for mode,roots in [('min',[r for r in source['root_policies'] if r['phase']==phase]),('mean',[r for r in results if r['phase']==phase])]:
  n=len(roots);bounds.append(dict(phase=phase,mode=mode,unit_canonical=str(sum(Fraction(r['goal_values'][unit]) for r in roots)/n),unit_favorable=str(sum(Fraction(r['tie_goal_max'][unit]) for r in roots)/n),any_grid_favorable=str(sum(max(Fraction(v) for v in r['tie_goal_max']) for r in roots)/n),true_goal_oracle=str(sum(Fraction(r['exact_goal_optimum']) for r in roots)/n)))
out=dict(complete=True,seconds=time.monotonic()-start,endpoint=endpoint,selected_heldout=str(heldmeans[selected]),unit=dict(train=str(means[unit]),heldout=str(heldmeans[unit])),bounds=bounds,models=models,root_policies=results,scope=D['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','seconds','endpoint','selected_heldout','unit','bounds')},indent=2))
