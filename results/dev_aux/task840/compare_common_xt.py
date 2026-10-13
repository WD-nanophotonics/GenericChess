import json,sys,math,time,hashlib
from pathlib import Path
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task880';O.mkdir(exist_ok=False);start=time.perf_counter();old=json.loads((R/'results/dev_aux/task849/result.json').read_bytes());assert json.loads((R/'results/dev_aux/task865/result.json').read_bytes())['status']=='PASS_ALL_PAIRED_INFORMATION_ABLATION_UPDATES_AND192_GAME_ERRORS'
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A
plan=dict(status='FROZEN_BEFORE_REEVALUATION',question='Do thetwoalready-fitted gamma1prices predict the same heldoutXt differently?',premise='DotcorrectedAxt/Bx0 informative-inputcomparison tocommonXt pricecomparison. Keep849models/oldoutputs/840endpoints untouched, no newfit/search.',data='All192originalprofile heldoutgames in qualified846; exactsameXt andtrue/censoredlabel/recordcounts/game-familyweights forbothfrozenmodels.',scope='Predictiontransfer ofprices only, notstrength/universalvalue; original849 remainsinformation-sourcecomparison, notpricecomparison.')
(O/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');games=[json.loads(l) for l in (R/'results/dev_aux/task846/games.jsonl').open(encoding='utf-8') if json.loads(l)['profile'].startswith('original_')];inventory=[]
for g in games:
 initial=g['profile'][9:];t=g['termination'];terminal=not t['kind'].startswith('cap');y=(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if terminal else g['raw_quantity']/19;X=[]
 for q in g['queries']:
  if q['player']!='candidate':continue
  b=A.replay(q['initial_sfen'],q['history']);x=[0]*16
  for sq in range(81):
   p=b.piece_at(sq)
   if p:x[A.MAP[p.piece_type]]+=1 if p.color==g['color'] else -1
  for c in [0,1]:
   for pt,n in b.pieces_in_hand[c].items():x[A.MAP[pt]]+=n*(1 if c==g['color'] else -1)
  x[8]=0;X.append(x)
 assert X;errors={arm:float(np.mean([(math.tanh(sum(a*b for a,b in zip(x,next(m['weights'] for m in old['models'] if m['initial']==initial and m['arm']==arm)))/1710)-y)**2 for x in X])) for arm in ['trajectory','first_candidate']};inventory.append(dict(initial=initial,pool=g['pool'],opponent=g['opponent'],family=g['root']['seed'],color=g['color'],terminal=terminal,label=y,records=len(X),errors=errors,trajectory_minus_first=errors['trajectory']-errors['first_candidate']))
rows=[]
for r in old['rows']:
 rr=[g for g in inventory if g['initial']==r['initial'] and g['pool']==r['pool'] and g['opponent']==r['opponent'] and (r['stratum']=='all' or g['terminal']==(r['stratum']=='terminal'))];families=sorted(set(g['family'] for g in rr));fm=[dict(family=f,mean_delta=float(np.mean([g['trajectory_minus_first'] for g in rr if g['family']==f]))) for f in families];row={k:r[k] for k in ['initial','pool','opponent','stratum','scope']};row.update(games=len(rr),families=len(families),mean_error={arm:float(np.mean([np.mean([g['errors'][arm] for g in rr if g['family']==f]) for f in families])) if families else None for arm in ['trajectory','first_candidate']},mean_delta=float(np.mean([f['mean_delta'] for f in fm])) if fm else None,by_family=fm);rows.append(row)
out=dict(status='ALL192_SHARED_XT_PRICE_PREDICTION_CORRECTION_COMPLETE',source_models_sha256=hashlib.sha256((R/'results/dev_aux/task849/result.json').read_bytes()).hexdigest(),game_inventory=inventory,rows=rows,new_go=0,new_fit_epochs=0,seconds=time.perf_counter()-start,scope=plan['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print([(r['initial'],r['opponent'],r['games'],r['mean_delta']) for r in rows if r['pool']=='validation' and r['stratum']=='terminal'])
