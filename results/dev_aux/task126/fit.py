"""Declared earlier-state prediction; no engine or human-value targets."""
import hashlib,json,math,statistics,time
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task126';started=time.monotonic();deadline=started+300
p=ROOT/'results/dev_aux/task124/controller.json';D=json.loads(p.read_bytes());assert D['completed'];rows=[];excluded=[]
for c in D['calls']:
 if time.monotonic()>deadline:raise TimeoutError('declared replay fuse')
 r=c['result'];x=c['context'];b=chess.Board()
 for m in r['opening']:b.push_uci(m)
 if len(r['actions'])<8:excluded.append(dict(name=x['name'],reason='ended_before8'));continue
 for m in r['actions'][:8]:b.push_uci(m)
 if b.is_game_over(claim_draw=False):excluded.append(dict(name=x['name'],reason='terminal_at8'));continue
 color=x['agent_color'];f=[1]+[len(b.pieces(k,color))-len(b.pieces(k,not color)) for k in (chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN)]
 s=r['score'];target=(1 if s['winner']==color else -1) if s['terminal'] and s['winner'] is not None else 0 if s['terminal'] else s['quantity_difference']/15
 rows.append(dict(name=x['name'],phase=x['phase'],opening_seed=x['opening_seed'],regime=int(x['name'].split('-p')[1].split('-')[0]),features=f,target=target,current_quantity=sum(f[1:])/15,terminal=s['terminal']))
train=[r for r in rows if r['phase']=='train'];test=[r for r in rows if r['phase']=='heldout'];assert not {r['opening_seed'] for r in train}&{r['opening_seed'] for r in test}
assert len({r['name'] for r in rows})==len(rows);assert train and test
A=[[sum(r['features'][i]*r['features'][j] for r in train)+(1 if i==j and i!=0 else 0) for j in range(6)] for i in range(6)]
b=[sum(r['features'][i]*r['target'] for r in train) for i in range(6)]
def solve(A,b):
 m=[a[:]+[t] for a,t in zip(A,b)]
 for j in range(len(b)):
  k=max(range(j,len(b)),key=lambda i:abs(m[i][j]));assert abs(m[k][j])>1e-12;m[j],m[k]=m[k],m[j]
  v=m[j][j];m[j]=[x/v for x in m[j]]
  for i in range(len(b)):
   if i!=j:
    v=m[i][j];m[i]=[a-v*z for a,z in zip(m[i],m[j])]
 return [r[-1] for r in m]
coef=solve(A,b);assert all(math.isfinite(x) for x in coef)
residual=max(abs(sum(A[i][j]*coef[j] for j in range(6))-b[i]) for i in range(6));assert residual<1e-8
mean=statistics.mean(r['target'] for r in train)
def pred(r):return sum(a*z for a,z in zip(coef,r['features']))
def metrics(group):
 if not group:return dict(n=0)
 def err(fn):
  errors=[fn(r)-r['target'] for r in group];return dict(MSE=statistics.mean(e*e for e in errors),MAE=statistics.mean(abs(e) for e in errors))
 return dict(n=len(group),distinct_opening_seeds=len({r['opening_seed'] for r in group}),ridge_material=err(pred),current_unit_quantity=err(lambda r:r['current_quantity']),training_mean=err(lambda r:mean))
result=dict(complete=True,scope='DeclaredTask126earlier8ply fixedhorizon mixed-policy prediction, not policy learning',data_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rows=len(rows),train_rows=len(train),heldout_rows=len(test),excluded=excluded,whole_game_split=True,disjoint_openings=True,lambda_ridge=1,coefficients=dict(zip(('intercept','P','N','B','R','Q'),coef)),linear_system_residual=residual,train_metrics=metrics(train),heldout_metrics=metrics(test),heldout_by_regime={str(op):metrics([r for r in test if r['regime']==op]) for op in (6,24)},heldout_terminal=metrics([r for r in test if r['terminal']]),heldout_cutoff=metrics([r for r in test if not r['terminal']]),training_target_mean=mean,model_and_target_fixed_before_run=True,human_values_used_to_fit=False,policy_deployed=False,clipped=False,limits='Repeated profiles/colors share8heldout opening seeds, not192independent draws. Counts only, no boardgeometry; training/heldout evolved-policy mixture, not causalpiecevalues, deploymentgain or universalprobability.',wall_seconds=time.monotonic()-started)
if abs(coef[1])>1e-10:result['signed_P_normalized_descriptive_coefficients']={k:v/coef[1] for k,v in zip('PNBRQ',coef[1:])}
(OUT/'prediction.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(OUT/'rows.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='excluded'},indent=2))