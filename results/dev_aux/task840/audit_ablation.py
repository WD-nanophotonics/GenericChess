import json,sys,time,math
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task865';O.mkdir(exist_ok=False);start=time.perf_counter();samp=[json.loads(l) for l in (R/'results/dev_aux/task844/samples.jsonl').open(encoding='utf-8')];result=json.loads((R/'results/dev_aux/task849/result.json').read_bytes());axes=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes())['optimization']['free_axes'];first={}
for s in samp:first.setdefault((s['initial_profile'],s['opponent'],s['family'],s['color']),s['features'])
checks=0;fd=0;maxerr=0
for m in result['models']:
 rr=[s for s in samp if s['initial_profile']==m['initial']];X=np.asarray([s['features'] if m['arm']=='trajectory' else first[s['initial_profile'],s['opponent'],s['family'],s['color']] for s in rr]);y=np.asarray([s['actual_outcome'] for s in rr]);aw=np.asarray([s['weight'] for s in rr]);hist=json.loads((R/'results/dev_aux/task849'/(m['initial']+'_'+m['arm']+'_epochs.json')).read_bytes());w=np.asarray(hist[0]['weights']);assert abs(aw.sum()-1)<1e-12
 for i,h in enumerate(hist):
  assert np.allclose(w,h['weights'],rtol=0,atol=1e-9);pred=np.tanh(X.dot(w)/1710);grad=np.asarray([np.dot((pred-y)*(1-pred**2)*aw,X[:,j])*w[j]/1710 for j in axes]);assert np.allclose(grad,h['gradient'],rtol=0,atol=1e-12);assert abs(np.dot(aw,(pred-y)**2)/2-h['loss'])<1e-12
  if i in [0,199]:
   for jj,j in enumerate(axes):
    eps=1e-5;wp=w.copy();wm=w.copy();wp[j]*=math.exp(eps);wm[j]*=math.exp(-eps);p=np.dot(aw,(np.tanh(X.dot(wp)/1710)-y)**2)/2;q=np.dot(aw,(np.tanh(X.dot(wm)/1710)-y)**2)/2;error=abs((p-q)/(2*eps)-grad[jj]);maxerr=max(maxerr,error);assert error<1e-8;fd+=1
  w[axes]=np.exp(np.clip(np.log(w[axes])-.5*grad,math.log(32),math.log(4096)));checks+=1
 assert np.allclose(w,m['weights'],rtol=0,atol=1e-9)
# IndependentPythonSFEN/feature replay andallgame errors.
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
physical=[json.loads(l) for l in (R/'results/dev_aux/task846/games.jsonl').open(encoding='utf-8') if json.loads(l)['profile'].startswith('original_')];assert len(physical)==len(result['game_inventory'])==192
for g,r in zip(physical,result['game_inventory']):
 initial=g['profile'][9:];t=g['termination'];royal=not t['kind'].startswith('cap');z=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if royal else g['raw_quantity']/19;xs=[]
 for q in g['queries']:
  if q['player']!='candidate':continue
  b=A.replay(q['initial_sfen'],q['history']);x=[0]*16
  for sq in range(81):
   p=b.piece_at(sq)
   if p:x[A.MAP[p.piece_type]]+=1 if p.color==g['color'] else -1
  for c in [0,1]:
   for pt,n in b.pieces_in_hand[c].items():x[A.MAP[pt]]+=n*(1 if c==g['color'] else -1)
  x[8]=0;xs.append(x)
 assert r['initial']==initial and r['family']==g['root']['seed'] and r['color']==g['color'] and r['label']==z and r['terminal']==royal
 for arm in ['trajectory','first_candidate']:
  w=next(m['weights'] for m in result['models'] if m['initial']==initial and m['arm']==arm);errors=[(math.tanh(sum(a*b for a,b in zip(x,w))/1710)-z)**2 for x in (xs if arm=='trajectory' else [xs[0]]*len(xs))];assert abs(sum(errors)/len(errors)-r['errors'][arm])<1e-12
out=dict(status='PASS_ALL_PAIRED_INFORMATION_ABLATION_UPDATES_AND192_GAME_ERRORS',epochs=checks,finite_differences=fd,max_fd_error=maxerr,allgame_errors=192,new_go=0,seconds=time.perf_counter()-start,scope='Bothgamma1 arms exactsame1486labels/weights andcandidateframe, featuresonlychange; all800epochs/96FD/all192heldoutgame errors independentlyrecomputed fromPythonpieces. Original840 .95fitsunchanged. No causalengineoruniversalpriceclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
