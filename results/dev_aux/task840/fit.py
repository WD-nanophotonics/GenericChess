import json,sys,math,hashlib,time
from pathlib import Path
import numpy as np
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task844';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes());assert json.loads((R/'results/dev_aux/task843/result.json').read_bytes())['status']=='PASS_ALL128_MC_TRAIN_ACTUAL';profiles=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes())['initial_profiles'];axes=plan['optimization']['free_axes'];gs=[json.loads(l) for l in (R/'results/dev_aux/task842/games.jsonl').open(encoding='utf-8')];start=time.perf_counter();endpoint=[];samples=[]
def phi(sfen,color):
 b=C.Board(sfen);x=np.zeros(16)
 for pc in b.pieces:
  if pc:x[pc%16]+=1 if (0 if pc<16 else 1)==color else -1
 for c,hand in enumerate(b.pieces_in_hand):
  for i,n in enumerate(hand):x[[1,2,3,4,7,5,6][i]]+=n*(1 if c==color else -1)
 x[8]=0;return x
for g in gs:
 queries=[q for q in g['queries'] if q['player']=='candidate'];t=g['termination'];z=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if not t['kind'].startswith('cap') else g['raw_quantity']/19
 assert queries
 for q in queries:
  b=C.Board(q['initial_sfen'])
  for u in q['history']:b.push_usi(u)
  x=phi(b.sfen(),g['color']);assert abs(float(x@np.asarray(q['weights']))-(int(q['state'].split()[3])*(1 if g['color']==0 else -1)))<1e-10
  samples.append(dict(initial_profile=g['initial_profile'],opponent=g['opponent'],family=g['root']['seed'],color=g['color'],ply=q['ply'],features=x.astype(int).tolist(),target=plan.get('gamma',.95)**(len(g['actions'])-q['ply']-1)*z,weight=1/(64*len(queries)),actual_outcome=z,sfen=b.sfen()))
(O/'samples.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in samples),encoding='utf-8');projected_initials=[]
for p in profiles:
 ss=[s for s in samples if s['initial_profile']==p['name']];X=np.asarray([s['features'] for s in ss]);y=np.asarray([s['target'] for s in ss]);aw=np.asarray([s['weight'] for s in ss]);assert abs(aw.sum()-1)<1e-10
 for method in plan['methods']:
  w=np.asarray(p['weights'],dtype=float);w[0]=w[8]=w[15]=0
  if method.endswith('projection'):w[14]=max(w[14],w[6]);w[13]=max(w[13],w[5])
  init=w.copy();th=np.log(w[axes]);hist=[]
  for epoch in range(200):
   pred=np.tanh(X@w/1710);err=pred-y;grad=np.sum((aw*err*(1-pred*pred))[:,None]*X[:,axes]*w[axes]/1710,axis=0);loss=float(.5*np.sum(aw*err*err));hist.append(dict(epoch=epoch,loss=loss,weights=w.tolist(),grad=grad.tolist()));th=np.clip(th-.5*grad,math.log(32),math.log(4096));w[axes]=np.exp(th)
   if method.endswith('projection'):w[14]=max(w[14],w[6]);w[13]=max(w[13],w[5]);th=np.log(w[axes])
  rounded=[int(math.floor(v+.5)) for v in w];rounded[1]=90;rounded[0]=rounded[8]=rounded[15]=0;name=method+'_'+p['name'];finalpred=np.tanh(X@np.asarray(rounded)/1710);endpoint.append(dict(name=name,initial_profile=p['name'],method=method,initial_weights=init.tolist(),weights=rounded,loss_before=hist[0]['loss'],loss_after_float=float(.5*np.sum(aw*(np.tanh(X@w/1710)-y)**2)),loss_after_rounded=float(.5*np.sum(aw*(finalpred-y)**2)),samples=len(ss),rank=int(np.linalg.matrix_rank(X[:,axes])),singular_values=np.linalg.svd(X[:,axes],compute_uv=False).tolist()));(O/(name+'_epochs.json')).write_text(json.dumps(hist,indent=2),encoding='utf-8')
 projected_initials.append(dict(name='projection_only_'+p['name'],weights=[int(max(p['weights'][i],p['weights'][6] if i==14 else p['weights'][5] if i==13 else p['weights'][i])) for i in range(16)]))
result=dict(status='ALL4_MC_ENDPOINTS_FROZEN_BEFORE_ANY_EVALUATION_REFERENCE',endpoints=endpoint,initial_projection_controls=projected_initials,seconds=time.perf_counter()-start,data_sha256=hashlib.sha256((R/'results/dev_aux/task842/games.jsonl').read_bytes()).hexdigest(),samples_sha256=hashlib.sha256((O/'samples.jsonl').read_bytes()).hexdigest(),scope='Uniformgame weighting64games/profile, exactrootmaterial features in fixedcandidateframe; gamma.95 everyplytoactualstoppingtime. Offline200logpricebatchepochs fixeddata; unroundedoptimizer androundeddeployment bothreported. Extrauntrainedprojection controls necessarytoattribute projectionseparately, declaredbeforeevaluation andwithoutreference. No labelhuman/sourcefitness/searchscoregradient/oldextraepoch.')
(O/'endpoints.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
