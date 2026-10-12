import json,time,hashlib,collections
from pathlib import Path
from fractions import Fraction
import numpy as np
import chess
R=Path.cwd();O=R/'results/dev_aux/task305';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task269/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task269/result.json').read_bytes());L=json.loads((R/'results/dev_aux/task296/result.json').read_bytes());start=time.monotonic();family={n:f for f,nn in D['families'].items() for n in nn};rows=[]
Decl=dict(task_id='305',question='Doeswithinroot/color materialvariationpredictfiniteH48 beyondgroupmeans andhowstable arewhole-root/familyfolds?',source='269all144train only;296endpoint remainsfrozennegative. OneX/y pergame@8. No newtimepoint/label/positivityconstraint/priceendpoint.',method='Groupdemean X/y by(root,color), oneOLSminimum norm. CoreoriginalnointerceptOLS andgroupmean+demeanedOLS diagnosticfolds: leaveonewholeTRAINroot orinitialpricefamilyout; allmeans/coefficients trainingfoldonly; unknown group usesglobaltrainingmeans. No bestfold/model adoption or newgames; two roots sensitivityonly.',advisor='1791810847 technicalobjection afterrawsave/reconcile; advisorread21fixedreport notnewlocaldata.',scope='Predictionassociation vspriceintervention remainseparate; samevector/fullline conflicts do notrefutepooledconditionalmeans orfixedpricesaveragedunderanexplicitdistribution.')
(O/'declaration.json').write_text(json.dumps(Decl,indent=2),encoding='utf-8')
for z in X['calls']:
 if z['phase']!='train':continue
 f=D['train_roots'][z['root']];b=chess.Board(f['initial_fen'])
 for t in f['history']:b.push_uci(t)
 prefix=[];feature=None;fen8=None
 for i,t in enumerate(z['actions']):
  m=chess.Move.from_uci(t);assert m in b.legal_moves;b.push(m)
  if i<8:prefix.append(t)
  if i==7:feature=[len(b.pieces(k,z['color']))-len(b.pieces(k,not z['color'])) for k in range(1,6)];fen8=b.fen()
 if feature is None:feature=[len(b.pieces(k,z['color']))-len(b.pieces(k,not z['color'])) for k in range(1,6)];fen8=b.fen()
 oo=b.outcome(claim_draw=False);y=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;y=y if oo is not None and oo.termination.name=='CHECKMATE' else 0;assert y==z['finite_mate_goal'];ref=next(v for v in L['train'] if v['name']==z['name'] and v['root']==z['root'] and v['color']==z['color']);assert feature==ref['x'] and y==ref['y'];rows.append(dict(name=z['name'],root=z['root'],color=z['color'],family=family[z['name']],x=feature,y=y,early_terminal=len(z['actions'])<8,fen8=fen8,fullprefix=f['history']+prefix))
A=np.array([z['x'] for z in rows],float);Y=np.array([z['y'] for z in rows],float);keys=[(z['root'],z['color']) for z in rows]
def grouped_fit(ix):
 ax=A[ix];yy=Y[ix];g=[k for k,i in zip(keys,ix) if i];means={k:(ax[[v==k for v in g]].mean(axis=0),yy[[v==k for v in g]].mean()) for k in set(g)};mx=np.array([means[k][0] for k in g]);my=np.array([means[k][1] for k in g]);w,_,rk,sv=np.linalg.lstsq(ax-mx,yy-my,rcond=None);return w,means,ax.mean(axis=0),yy.mean(),int(rk),sv,my+(ax-mx)@w,my
allix=np.ones(len(rows),bool);w,means,gx,gy,rk,sv,pred,base=grouped_fit(allix);folds=[]
for typ,values in [('root',[0,1]),('family',list(D['families']))]:
 for val in values:
  ix=np.array([z[typ]!=val for z in rows]);ww,mm,globalX,globalY,rank,sing,_,_=grouped_fit(ix);oo,_,r2,s2=np.linalg.lstsq(A[ix],Y[ix],rcond=None);test=[z for z,i in zip(rows,ix) if not i];pp=[];bb=[]
  for z in test:mx,my=mm.get((z['root'],z['color']),(globalX,globalY));bb.append(my);pp.append(my+(np.array(z['x'])-mx)@ww)
  true=Y[~ix];folds.append(dict(type=typ,held=val,train=int(ix.sum()),test=int((~ix).sum()),within_rank=rank,within_coefficients=dict(zip('PNBRQ',map(float,ww))),originalOLS_coefficients=dict(zip('PNBRQ',map(float,oo))),groupbaseline_test_MSE=float(np.mean((np.array(bb)-true)**2)),withinOLS_test_MSE=float(np.mean((np.array(pp)-true)**2)),originalOLS_test_MSE=float(np.mean((A[~ix]@oo-true)**2)),globaltrainmean_test_MSE=float(np.mean((globalY-true)**2))))
count=collections.defaultdict(list);state=collections.defaultdict(list)
for z in rows:count[(z['root'],z['color'],tuple(z['x']))].append(z['y']);state[(z['root'],z['color'],tuple(z['fullprefix']))].append(z)
floor=sum(sum((Fraction(v)-sum(map(Fraction,vv))/len(vv))**2 for v in vv) for vv in count.values())/len(rows);conflict=[vv for vv in state.values() if len({z['y'] for z in vv})>1]
out=dict(complete=True,source_feature_target_checks=len(rows),new_games=0,early_terminal_absorbed=sum(z['early_terminal'] for z in rows),within_group_rank=rk,within_group_singular=list(map(float,sv)),within_group_coefficients=dict(zip('PNBRQ',map(float,w))),group_baseline_train_MSE=float(np.mean((base-Y)**2)),within_group_train_MSE=float(np.mean((pred-Y)**2)),group_count_conditional_lower_MSE=str(floor),same_fullhistory_different_target_groups=len(conflict),first3_conflict_examples=[vv[:4] for vv in conflict[:3]],folds=folds,seconds=time.monotonic()-start,scope=Decl['scope'])
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='first3_conflict_examples'},indent=2))