"""Training-only finite material return regression; no new engine execution."""
import json,math,time,datetime,hashlib,importlib.util
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task173';D=json.loads((O/'declaration.json').read_bytes())
sp=importlib.util.spec_from_file_location('P173',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
def row(c):
 r=c['result'];x=c['context'];b=chess.Board(r['root_fen'])
 for m in r['opening_history']:b.push_uci(m)
 if len(r['actions'])<8:return None
 for m in r['actions'][:8]:b.push_uci(m)
 if b.is_game_over(claim_draw=False):return None
 color=x['agent_color'];features=[1]+[len(b.pieces(i,color))-len(b.pieces(i,not color)) for i in range(1,6)];sc=r['score']
 bounded=(0 if sc['winner'] is None else (1 if sc['winner']==color else -1)) if sc['terminal'] else sc['quantity_difference']/15
 return dict(features=features,phase=x['phase'],opponent=x['opponent'],root_index=x['root_index'],name=x['name'],final_terminal=sc['terminal'],targets=dict(bounded_terminal_1_else_unitdiff15=bounded,final_unitdiff15_including_terminal=sc['quantity_difference']/15))
def metrics(actual,pred):return dict(n=len(actual),mse=float(np.mean((actual-pred)**2)),mae=float(np.mean(np.abs(actual-pred))),target_mean=float(np.mean(actual)))
def execute():
 if (O/'analysis.json').exists():raise FileExistsError('frozen')
 started=time.monotonic();P.stop();source=R/'results/dev_aux/task169/controller.json';C=json.loads(source.read_bytes());assert C['completed'];train=[];held=[];excluded=dict(train={},heldout={})
 for phase,output in (('train',train),):
  for i,c in enumerate(C['calls']):
   if c['context']['phase']!=phase:continue
   if i%64==0:
    P.stop();assert time.monotonic()-started<300
   x=row(c)
   if x is None:
    key=c['context']['opponent'];excluded[phase][key]=excluded[phase].get(key,0)+1
   else:output.append(x)
 models=[]
 for opponent in ('random','unit2ply','pooled'):
  group=[r for r in train if opponent=='pooled' or r['opponent']==opponent];X=np.asarray([r['features'] for r in group],dtype=float);assert len(X)>6
  rank=int(np.linalg.matrix_rank(X));centered=X[:,1:]-np.mean(X[:,1:],axis=0);eigen=np.linalg.eigvalsh(centered.T@centered)
  for target in D['targets']:
   y=np.asarray([r['targets'][target] for r in group]);pen=np.diag([0]+[1]*5);coef=np.linalg.solve(X.T@X+pen,X.T@y)
   assert np.all(np.isfinite(coef))
   byfeatures={}
   for feature,target_v in zip(X,y):byfeatures.setdefault(tuple(feature[1:]),[]).append(float(target_v))
   within_sse=sum(sum((v-sum(vv)/len(vv))**2 for v in vv) for vv in byfeatures.values())
   support=dict(unique_material_vectors=len(byfeatures),within_identical_material_mse_lower_bound=within_sse/len(y),nonconstant_target_vector_groups=sum(max(vv)-min(vv)>1e-12 for vv in byfeatures.values()),scope='Empirical training-only minimum residual of any deterministic count-vector predictor on these exposed data; notholdoutbound, causalproof orrefutation of distribution-averaged piecevalues.')
   models.append(dict(opponent=opponent,target=target,coefficients=coef.tolist(),training_target_mean=float(np.mean(y)),empirical_material_alias_support=support,training_n=len(X),training_feature_rank=rank,centered_material_gram_eigenvalues=eigen.tolist(),nonzero_countdiff_per_type=dict(zip('PNBRQ',map(int,np.sum(X[:,1:]!=0,axis=0)))),training_metrics=metrics(y,X@coef)))
 frozen=dict(complete=True,all_models_frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),models=models,source_controller_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='All six fits use training only and written before heldout feature/target evaluation; whole original controller loaded, no blind method-discovery claim.')
 (O/'models.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
 # No fit/model/lambda decisions below this point.
 for i,c in enumerate(C['calls']):
  if c['context']['phase']!='heldout':continue
  if i%32==0:P.stop()
  x=row(c)
  if x is None:
   key=c['context']['opponent'];excluded['heldout'][key]=excluded['heldout'].get(key,0)+1
  else:held.append(x)
 results=[]
 for model in models:
  group=[r for r in held if model['opponent']=='pooled' or r['opponent']==model['opponent']];X=np.asarray([r['features'] for r in group],dtype=float);y=np.asarray([r['targets'][model['target']] for r in group]);coef=np.asarray(model['coefficients']);cur=np.sum(X[:,1:],axis=1)/15;constant=np.full(len(y),model['training_target_mean']);beta=coef[1:];pnorm={k:float(v/beta[0]) for k,v in zip('PNBRQ',beta)} if abs(beta[0])>1e-12 else None;positive=bool(np.all(beta>0))
  dist=float(np.mean([abs(math.log(pnorm[k]/D['human_reference'][k])) for k in 'NBRQ'])) if pnorm and positive else None
  perroot=[]
  for idx in sorted({r['root_index'] for r in group}):
   mask=np.asarray([r['root_index']==idx for r in group]);perroot.append(dict(root_index=idx,model=metrics(y[mask],(X@coef)[mask]),current_unit=metrics(y[mask],cur[mask])))
  results.append(dict(**model,heldout=metrics(y,X@coef),heldout_current_unit=metrics(y,cur),heldout_trainmean=metrics(y,constant),heldout_terminal_games=sum(r['final_terminal'] for r in group),Pnormalized=pnorm,all_positive_material_coefficients=positive,descriptive_reference_distance=dist,heldout_per_root=perroot))
 out=dict(complete=True,train_rows=len(train),heldout_rows=len(held),excluded_terminal_at8=excluded,all_models_frozen_at=frozen['all_models_frozen_at'],results=results,wall_seconds=time.monotonic()-started,scope='Exploratory distribution-conditioned return prediction; sparse labels/position omitted. Predictiongain isnotcausalprice/policygain; negativecoefficients kept, nohumanfit ornewgames.')
 (O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,rows=[len(train),len(held)],excluded=excluded,results=[{k:r[k] for k in ('opponent','target','Pnormalized','all_positive_material_coefficients','descriptive_reference_distance','heldout','heldout_current_unit','heldout_trainmean','training_feature_rank','nonzero_countdiff_per_type')} for r in results],seconds=out['wall_seconds']),indent=2))
if __name__=='__main__':execute()
