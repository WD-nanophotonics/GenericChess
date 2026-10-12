import json,time,hashlib,collections
from pathlib import Path
from fractions import Fraction
import numpy as np
import chess
R=Path.cwd();O=R/'results/dev_aux/task296';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task269/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task269/result.json').read_bytes());E=json.loads((R/'results/dev_aux/task269/endpoints.json').read_bytes());start=time.monotonic()
Decl=dict(task_id='296',question='Do frozencheapmate-by48 labels identify a positive5piece materialdirection from a fixedearlycountvector, withouthumanparameters?',train_source='269144actualtrain trajectories',feature='AgentPNBRQboardcountdiff afterfirst8half-moves; oneequalweight rowpergame; no intercept; all5 coefficients OLSminimumL2norm, not scaledprice untilrank5/allpositive',target='Finiteactualmate signby48; everyunknown/draw0 finitegoal, never finaldrawWDL',fit='One numpy.linalg.lstsq rcond=None; no hyperparameters/search/seed/labelselection. Fit endpointwritten before developmentfeatures read/evaluated. Leave-oneTRAINroot diagnostics only; do notselectbestendpoint. Positivefixedpieceinterpretation allowedonlyifall5 >0 andrank5; otherwise routefails andno enginequery/adoption. Humanlabelsneverread.',scope='Source144 contains36behaviorpricepolicies on2oldroots*2colors, heavilycorrelated. Olddevelopment exposed, nofreshholdout. Coefficientsnotuniversalmaterialvalues; policycoverage/terminalconfounding anticipated.',source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'results/dev_aux/task269/declaration.json',R/'results/dev_aux/task269/result.json']})
(O/'declaration.json').write_text(json.dumps(Decl,indent=2),encoding='utf-8')
def feature(z,roots):
 f=roots[z['root']];b=chess.Board(f['initial_fen'])
 for text in f['history']+z['actions'][:8]:b.push_uci(text)
 return [len(b.pieces(i+1,z['color']))-len(b.pieces(i+1,not z['color'])) for i in range(5)]
train=[dict(name=z['name'],root=z['root'],color=z['color'],x=feature(z,D['train_roots']),y=z['finite_mate_goal']) for z in X['calls'] if z['phase']=='train'];assert len(train)==144
A=np.array([z['x'] for z in train],float);y=np.array([z['y'] for z in train],float);w,res,rank,sv=np.linalg.lstsq(A,y,rcond=None);fit=A@w;groups=collections.defaultdict(list)
for z in train:groups[tuple(z['x'])].append(z['y'])
countfloor=sum(sum((Fraction(v)-sum(map(Fraction,yy))/len(yy))**2 for v in yy) for yy in groups.values())/len(train)
endpoint=dict(coefficients=dict(zip('PNBRQ',map(float,w))),rank=int(rank),singular_values=list(map(float,sv)),positive_price_direction=bool(rank==5 and all(w>0)),fit_MSE=float(np.mean((fit-y)**2)),count_only_irreducible_MSE=str(countfloor),frozen_at=time.time(),source_sha=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest())
(O/'endpoint.json').write_text(json.dumps(endpoint,indent=2),encoding='utf-8')
leave=[]
for keep in (0,1):
 ix=np.array([z['root']==keep for z in train]);ww,rr,rk,ss=np.linalg.lstsq(A[ix],y[ix],rcond=None);leave.append(dict(training_root=keep,coefficients=dict(zip('PNBRQ',map(float,ww))),rank=int(rk),train_MSE=float(np.mean((A[ix]@ww-y[ix])**2)),other_root_MSE=float(np.mean((A[~ix]@ww-y[~ix])**2))))
# Endpoint exists before any development feature construction.
assert (O/'endpoint.json').exists();dev=[dict(name=z['name'],root=z['root'],color=z['color'],x=feature(z,D['development_roots']),y=z['finite_mate_goal']) for z in X['calls'] if z['phase']=='development'];AA=np.array([z['x'] for z in dev],float);yy=np.array([z['y'] for z in dev],float);pred=AA@w
out=dict(complete=True,new_games=0,train_rows=len(train),physical_development_rows=len(dev),fit=endpoint,leave_one_training_root=leave,unique_count_vectors=len(groups),conflicting_count_vectors=sum(len(set(yy))>1 for yy in groups.values()),ambiguous_groups=[dict(x=x,labels=vv) for x,vv in groups.items() if len(set(vv))>1],train=train,development=[dict(**z,prediction=float(pr)) for z,pr in zip(dev,pred)],development_MSE=float(np.mean((pred-yy)**2)),development_zero_predictor_MSE=float(np.mean(yy**2)),training_zero_predictor_MSE=float(np.mean(y**2)),seconds=time.monotonic()-start,scope=Decl['scope'],decision='FAIL_positive_direction/no price normalization, clipping,enginegame oradoption' if not endpoint['positive_price_direction'] else 'Positivefivecoeffdirection candidate only; needexplicit normalization/backendquery declaration, not automatic adoption')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('train','development','ambiguous_groups')},indent=2))