
from pathlib import Path
from fractions import Fraction as F
import json,chess,collections
R=Path.cwd();O=R/'results/dev_aux/task1200';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task1199/plan.json').read_bytes());gs=[json.loads(s) for s in (R/'results/dev_aux/task1154/games.jsonl').read_text().splitlines()]
samples=[]
for g in gs:
 b=chess.Board(g['root']['fen8']);state_limit=min(12,len(g['actions'])-1)
 for offset in range(state_limit+1):
  if offset:b.push_uci(g['actions'][offset-1]['move'])
  # nonterminalstates: originalaudit alreadyrules/time authoritative
  assert b.fen()==(g['root']['fen8'] if offset==0 else g['actions'][offset-1]['after'])
  d={t:len(b.pieces(t,b.turn))-len(b.pieces(t,not b.turn)) for t in [chess.ROOK,chess.KNIGHT]}
  z=0 if g['opponent']=='unit_search' else (1 if b.turn==g['color'] else -1)
  label='C';y=F(0);term=g['termination']
  if g['label']!='C' and len(g['actions'])<=offset+12:
   label='D' if term['winner'] is None else 'W' if term['winner']==b.turn else 'L';y=F((label=='W')-(label=='L'))
  samples.append(dict(seed=g['root']['seed'],episode=g['game'],offset=offset,fen=b.fen(),history=[a['move'] for a in g['actions'][:offset]],opponent=g['opponent'],color=g['color'],stm=b.turn,x=[d[chess.ROOK],d[chess.KNIGHT],z],label=label,y=str(y),final_time=len(g['actions']),train=g['root']['composition_ordinal']<4,composition=g['root']['composition']))
with (O/'samples.jsonl').open('x') as f:
 for v in samples:f.write(json.dumps(v)+'\n')
def weighted(ss):
 families=collections.Counter(v['seed'] for v in ss);episodes=collections.Counter(v['episode'] for v in ss);ne={seed:len(set(v['episode'] for v in ss if v['seed']==seed)) for seed in families}
 return [(list(map(F,v['x'])),F(v['y']),F(1,len(families)*ne[v['seed']]*episodes[v['episode']])) for v in ss]
def fit(ss):
 rows=weighted(ss);a=[[sum(w*x[i]*x[j] for x,y,w in rows) for j in range(3)]+[sum(w*x[i]*y for x,y,w in rows)] for i in range(3)]
 for j in range(3):
  k=next((i for i in range(j,3) if a[i][j]),None)
  if k is None:return None
  a[j],a[k]=a[k],a[j];z=a[j][j];a[j]=[x/z for x in a[j]]
  for i in range(3):
   if i!=j:z=a[i][j];a[i]=[x-z*y for x,y in zip(a[i],a[j])]
 return [a[i][-1] for i in range(3)]
def mse(ss,b):return str(sum(w*(sum(q*c for q,c in zip(x,b))-y)**2 for x,y,w in weighted(ss)))
train=[v for v in samples if v['train']];dev=[v for v in samples if not v['train']];rows=[]
for name,ss in [('rootH12',[v for v in train if v['offset']==0]),('reachedH12',train)]:
 b=fit(ss);ratio=b[0]/b[1] if b and b[0]>0 and b[1]>0 else None;r=round(720*ratio) if ratio else None
 rows.append(dict(model=name,training_samples=len(ss),families=len(set(v['seed'] for v in ss)),coef=list(map(str,b)) if b else None,positive_ratio=str(ratio) if ratio else None,candidateR=r,supported=bool(r and 1<=r<=3328),train_MSE=mse(ss,b) if b else None,dev_reached_MSE=mse(dev,b) if b else None,dev_root_MSE=mse([v for v in dev if v['offset']==0],b) if b else None))
(O/'result.json').write_text(json.dumps(dict(status='EXACT_WEIGHTED_REACHED_STATE_H12_VALUE_DIAGNOSTIC',samples=len(samples),rows=rows,label_counts=dict(collections.Counter(v['label'] for v in samples)),new_go=0,scope=D),indent=2));print(rows,'SAMPLES',len(samples))
