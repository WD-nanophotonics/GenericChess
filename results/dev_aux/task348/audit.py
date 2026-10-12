"""Independent scaled-integer finite-epsilon checks of all axis and mixed slopes."""
import json,time,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task348';assert not (O/'audit.json').exists();start=time.monotonic();A=json.loads((R/'results/dev_aux/task347/audit.json').read_bytes());T={z['root']:z for z in [json.loads(l) for l in (R/'results/dev_aux/task346/trees.jsonl').read_bytes().splitlines()]};scale=2**20;checked=0;stats={};details=[]
def evaluate(t,weights):
 values=[]
 for z in t['nodes']:
  if 't'in z:v=z['t']*scale
  elif 'v'in z:v=sum(w*x for w,x in zip(weights,z['v']))
  else:v=(max if z['op']=='max' else min)(values[ch] for u,ch in z['children'])
  values.append(v)
 return values[t['root_index']]
for z in A['details']:
 t=T[z['root']];w=[z['weights'][k]*scale for k in 'PNBRQ'];base=evaluate(t,w);assert base==z['score']*scale
 for j in range(5):
  plus=w.copy();minus=w.copy();plus[j]+=1;minus[j]-=1;rp=evaluate(t,plus)-base;lp=base-evaluate(t,minus);assert (lp,rp)==(z['left'][j],z['right'][j]);checked+=2
 for i,d in enumerate(A['directions']):
  v=w.copy()
  for j,a in enumerate(d):v[j+1]+=a
  assert evaluate(t,v)-base==z['mixed_directions'][i];checked+=1
 group=stats.setdefault(z['profile'],dict(cases=0,axis_kinks=0,axis_PV_mismatches=0,mixed_PV_mismatches=0));group['cases']+=1;group['axis_kinks']+=z['axis_nondifferentiable'];group['axis_PV_mismatches']+=z['PV_axis_mismatch'];group['mixed_PV_mismatches']+=z['mixed_mismatches']
 if z['PV_axis_mismatch'] or z['mixed_mismatches']:details.append({k:z[k] for k in ('root','profile','score','PV_vector','left','right','axis_nondifferentiable','PV_axis_mismatch','mixed_mismatches')})
print('PASS',checked,stats)
out=dict(complete=True,scaled_integer_finite_difference_checks=checked,epsilon='1/1048576',groups=stats,counterexamples=details,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task347/audit.json').read_bytes()).hexdigest(),proof='Allbaseleafvalues integers; strictgap>=1. Eachcoordinatecountdifference boundedby15per side. Fourcoordinate mixedslopedifference<=120, so epsilon1/2^20 cannotcrossstrictleafordering; max/min finite differences exactly directionalderivatives onthiscomplete tree. Terminalvalues scaledsame. Pchanges analyticalonly, notactualLearnerP208 whichfixed.',scope='No extraNativeorMaturequeries, fit, humanlabels ornewgeneration. Bothone-sided axes andall32fixedmixedrays qualified. ActualPV leafvector often fails directionalsensitivity atunit andsomelearnedintegerweights; neitheruniversalTDfailure nor reason torequirefullWDL/all-defense beforeboundednewmethod.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')