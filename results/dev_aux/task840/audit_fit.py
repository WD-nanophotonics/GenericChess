import json,sys,math,time,hashlib
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task845';O.mkdir(exist_ok=False);start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G
plan=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes());axes=plan['optimization']['free_axes'];gs=[json.loads(l) for l in (R/'results/dev_aux/task842/games.jsonl').open(encoding='utf-8')];ss=[json.loads(l) for l in (R/'results/dev_aux/task844/samples.jsonl').open(encoding='utf-8')];ep=json.loads((R/'results/dev_aux/task844/endpoints.json').read_bytes());si=0;counts=dict(samples=0,epochs=0,finite_difference_checks=0);fdmax=0
for g in gs:
 qq=[q for q in g['queries'] if q['player']=='candidate'];t=g['termination'];z=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if not t['kind'].startswith('cap') else g['raw_quantity']/19
 for q in qq:
  row=ss[si];si+=1;b=A.replay(q['initial_sfen'],q['history']);phi=[0]*16
  for sq in range(81):
   p=b.piece_at(sq)
   if p:phi[A.MAP[p.piece_type]]+=1 if p.color==g['color'] else -1
  for c in [0,1]:
   for p,n in b.pieces_in_hand[c].items():phi[A.MAP[p]]+=n*(1 if c==g['color'] else -1)
  phi[8]=0;assert row['features']==phi and row['sfen'].split()[:3]==b.sfen().split()[:3];assert abs(row['target']-.95**(len(g['actions'])-q['ply']-1)*z)<1e-12;assert row['weight']==1/(64*len(qq));assert row['family']==g['root']['seed'] and row['color']==g['color'] and row['initial_profile']==g['initial_profile'];counts['samples']+=1
assert si==len(ss)
for e in ep['endpoints']:
 rows=[s for s in ss if s['initial_profile']==e['initial_profile']];X=np.asarray([s['features'] for s in rows]);y=np.asarray([s['target'] for s in rows]);aw=np.asarray([s['weight'] for s in rows]);w=np.asarray(e['initial_weights']);h=json.loads((R/'results/dev_aux/task844'/(e['name']+'_epochs.json')).read_bytes());assert len(h)==200
 for i,row in enumerate(h):
  assert np.allclose(w,row['weights'],rtol=0,atol=2e-10);pred=np.tanh(X.dot(w)/1710);delta=(pred-y)*(1-pred**2)*aw;grad=np.asarray([float(np.dot(delta,X[:,j])*w[j]/1710) for j in axes]);assert np.allclose(grad,row['grad'],rtol=0,atol=2e-12);loss=float(np.dot(aw,(pred-y)**2)/2);assert abs(loss-row['loss'])<1e-12
  if i in [0,199]:
   for jj,j in enumerate(axes):
    eps=1e-5;wp=w.copy();wm=w.copy();wp[j]*=math.exp(eps);wm[j]*=math.exp(-eps);lp=float(np.dot(aw,(np.tanh(X.dot(wp)/1710)-y)**2)/2);lm=float(np.dot(aw,(np.tanh(X.dot(wm)/1710)-y)**2)/2);err=abs((lp-lm)/(2*eps)-grad[jj]);fdmax=max(fdmax,err);assert err<1e-8;counts['finite_difference_checks']+=1
  th=np.clip(np.log(w[axes])-.5*grad,math.log(32),math.log(4096));w[axes]=np.exp(th)
  if e['method'].endswith('projection'):w[14]=max(w[14],w[6]);w[13]=max(w[13],w[5])
  counts['epochs']+=1
 assert e['weights']==[int(math.floor(v+.5)) for v in w]
out=dict(status='PASS_ALL_EXACT_FEATURE_LABEL_LOGGRAD_AND4_ENDPOINTS',counts=counts,max_finite_difference_error=fdmax,seconds=time.perf_counter()-start,new_go=0,scope='Independentpythonshogi features andfullhistory labels fromactualqueries; all800updateepochs recreated withindependentmatrixgradientexpression;192 finite-difference checks onfirst/lastepochs. Uniformgame weighting/sideframe/clamps/projection/rounding actualverified. Fitlossnotvaluelearningcertificate.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
