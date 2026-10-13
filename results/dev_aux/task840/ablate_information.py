import json,time,math,sys,collections
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task849';O.mkdir(exist_ok=False);p=dict(status='FROZEN_BEFORE_DIAGNOSTIC_FITS',arms=['trajectory','first_candidate'],gamma=1,epochs=200,lr=.5,free12='840sameaxes/clamps/P90K0',data='842allactualtrain records; sameeveryrow actualundiscountedlabel andweight, onlyfeatureschange tofirstcandidateofthatgame. Original840unchanged.',evaluation='846qualifiedONLYoriginalunit/random profilesmatchingtraininginitial; all24newfamilies eachsamegame labels/records/weights, squared errors bycompletefamily, terminal/censoredseparately; no timesteprandomsplit, no newgame/priceadoption.',scope='Dotminimalinformation-sourceablation; gamma1both removesdiscounttimecue butlaterfeatures still closer to outcome, notenginecausality/playingstrength.')
(O/'plan.json').write_text(json.dumps(p,indent=2),encoding='utf-8');train=[json.loads(l) for l in (R/'results/dev_aux/task844/samples.jsonl').open(encoding='utf-8')];axes=json.loads((R/'results/dev_aux/task840/plan.json').read_bytes())['optimization']['free_axes'];originals=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes())['initial_profiles'];start=time.perf_counter();first={};models=[]
for s in train:first.setdefault((s['initial_profile'],s['opponent'],s['family'],s['color']),s['features'])
for initial in originals:
 rows=[s for s in train if s['initial_profile']==initial['name']];y=np.asarray([s['actual_outcome'] for s in rows]);aw=np.asarray([s['weight'] for s in rows])
 for arm in p['arms']:
  X=np.asarray([s['features'] if arm=='trajectory' else first[s['initial_profile'],s['opponent'],s['family'],s['color']] for s in rows]);w=np.asarray(initial['weights'],dtype=float);hist=[]
  for epoch in range(200):
   pred=np.tanh(X@w/1710);err=pred-y;loss=float(np.dot(aw,err*err)/2);grad=np.sum((aw*err*(1-pred*pred))[:,None]*X[:,axes]*w[axes]/1710,axis=0);hist.append(dict(epoch=epoch,weights=w.tolist(),loss=loss,gradient=grad.tolist()));w[axes]=np.exp(np.clip(np.log(w[axes])-.5*grad,math.log(32),math.log(4096)))
  models.append(dict(initial=initial['name'],arm=arm,weights=w.tolist(),loss_before=hist[0]['loss'],loss_after=float(np.dot(aw,(np.tanh(X@w/1710)-y)**2)/2),rank=int(np.linalg.matrix_rank(X[:,axes]))));(O/(initial['name']+'_'+arm+'_epochs.json')).write_text(json.dumps(hist,indent=2),encoding='utf-8')
# Nativefeatures fromactualsavedquery forqualifiedoldoriginalvalidation, noenginecalls.
sys.path.insert(0,str(R/'results/dev_aux/task840'));import cshogi as C
def phi(sfen,color):
 b=C.Board(sfen);x=np.zeros(16)
 for pc in b.pieces:
  if pc:x[pc%16]+=1 if (0 if pc<16 else 1)==color else -1
 for c,hand in enumerate(b.pieces_in_hand):
  for i,n in enumerate(hand):x[[1,2,3,4,7,5,6][i]]+=n*(1 if c==color else -1)
 x[8]=0;return x
outrows=[];inventory=[]
for line in (R/'results/dev_aux/task846/games.jsonl').open(encoding='utf-8'):
 g=json.loads(line)
 if not g['profile'].startswith('original_'):continue
 initial=g['profile'][9:];qq=[q for q in g['queries'] if q['player']=='candidate'];assert qq;features=[]
 for q in qq:
  b=C.Board(q['initial_sfen'])
  for u in q['history']:b.push_usi(u)
  features.append(phi(b.sfen(),g['color']))
 t=g['termination'];terminal=not t['kind'].startswith('cap');z=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if terminal else g['raw_quantity']/19
 errors={}
 for arm in p['arms']:
  w=np.asarray(next(m['weights'] for m in models if m['initial']==initial and m['arm']==arm));xs=features if arm=='trajectory' else [features[0]]*len(features);errors[arm]=float(np.mean([(math.tanh(float(x@w)/1710)-z)**2 for x in xs]))
 inventory.append(dict(initial=initial,pool=g['pool'],opponent=g['opponent'],family=g['root']['seed'],color=g['color'],terminal=terminal,label=z,records=len(qq),errors=errors,trajectory_minus_first=errors['trajectory']-errors['first_candidate']))
for initial in [p['name'] for p in originals]:
 for pool in ['development','validation']:
  for opp in ['unit','random2514']:
   for stratum in ['all','terminal','censored']:
    rs=[r for r in inventory if r['initial']==initial and r['pool']==pool and r['opponent']==opp and (stratum=='all' or r['terminal']==(stratum=='terminal'))];families=sorted(set(r['family'] for r in rs));fm=[dict(family=f,mean_delta=float(np.mean([r['trajectory_minus_first'] for r in rs if r['family']==f]))) for f in families];row=dict(initial=initial,pool=pool,opponent=opp,stratum=stratum,games=len(rs),families=len(families),mean_error={arm:float(np.mean([np.mean([r['errors'][arm] for r in rs if r['family']==f]) for f in families])) if families else None for arm in p['arms']},mean_delta=float(np.mean([f['mean_delta'] for f in fm])) if fm else None,by_family=fm,scope='Stratumfamilies withoutthisoutcome excludedonlythisdescriptiveerrorstratum; all-gamecomparisonkeepsallfamilies. No teststrength.' );outrows.append(row)
(O/'result.json').write_text(json.dumps(dict(status='ALL_ZERO_GO_PAIRED_TRAJECTORY_FIRST_ABLATION',models=models,rows=outrows,game_inventory=inventory,seconds=time.perf_counter()-start,new_go=0,scope=p['scope']),indent=2),encoding='utf-8');print('ABLATION',len(inventory),'games',len(outrows),'rows',round(time.perf_counter()-start,3));print([r for r in outrows if r['pool']=='validation' and r['stratum']=='terminal'])
