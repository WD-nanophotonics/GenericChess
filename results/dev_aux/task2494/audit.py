"""Replay real Chess records and assess learning curves without training/selection."""
from pathlib import Path
from collections import Counter
import json,math,chess,hashlib
OUT=Path('results/dev_aux/task2494')
def run():
 train=Path('results/dev_aux/task2492');result=json.loads((train/'result.json').read_text());plan=json.loads((train/'plan.json').read_text());curves=[json.loads(x)for x in(train/'curves.jsonl').read_text().splitlines()];games=[json.loads(x)for x in(train/'games.jsonl').read_text().splitlines()];checks=0
 for g in games:
  record=g['record'];b=chess.Board(record['initial'])
  for u in record['moves']:
   m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);checks+=1
  assert b.fen()==record['fen'];o=b.outcome(claim_draw=True);v=None if o is None else 0 if o.winner is None else 1 if o.winner else-1
  assert v==g['outcome'];assert(g['ending']=='ACTUAL_TERMINAL')==(v is not None)
 corrected=[];summaries=[]
 for arm in result['arms']:
  rows=[r for r in curves if r['seed']==arm['seed']and r['method']==arm['method']];current=arm['initial'];xs=[]
  for row in rows:
   assert row['weights'][0]==1 and all(map(math.isfinite,row['weights']))
   if 'before'in row:assert row['before']==current
   current=row['weights']
   if row.get('loss')is not None:assert row['loss']>=0 and math.isfinite(row['loss']);xs.append(row['loss'])
  assert current==arm['weights']
  gr=[g for g in games if g['seed']==arm['seed']and g['method']==arm['method']]
  assert sum(g['nodes']for g in gr)==arm['nodes']<=plan['node_budget_per_arm']
  actual_reason='MAX_GAMES'if len(gr)==plan['max_games']and arm['nodes']<plan['node_budget_per_arm']else arm['reason']
  if actual_reason!=arm['reason']:corrected.append(dict(seed=arm['seed'],method=arm['method'],reported=arm['reason'],actual=actual_reason,reason='Original runner default reason not changed after8game loop exhaustion; no data loss or budget excess. Original result preserved.'))
  n=max(1,len(xs)//4);summaries.append(dict(seed=arm['seed'],method=arm['method'],samples=arm['training_samples'],weights=arm['weights'],first_quarter_loss=sum(xs[:n])/n,last_quarter_loss=sum(xs[-n:])/n,scope='On-policy changing-state losses, NOT fixed validation loss or proof of improvement.'))
 evaluation=Path('results/dev_aux/task2493');pairs=[];replayed_eval=0
 if(evaluation/'result.json').exists():
  rows=[json.loads(x)for x in(evaluation/'games.jsonl').read_text().splitlines()];by={}
  for row in rows:
   b=chess.Board(row['record']['initial'])
   for u in row['record']['moves']:
    m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);replayed_eval+=1
   assert b.fen()==row['record']['fen'];o=b.outcome(claim_draw=True);v=None if o is None else 0 if o.winner is None else 1 if o.winner else-1;assert row['reward']==(None if v is None else v*(1 if row['color']==0 else-1))
   key=tuple(row[k]for k in('seed','method','prefix_seed','color'));by.setdefault(key,{})[row['treatment']]=row
  for key,v in by.items():
   assert set(v)=={'initial','learned'};a,b=v['initial'],v['learned'];assert a['initial_record']==b['initial_record']
   def bounds(x):return(-1,1)if x is None else(x,x)
   al,au=bounds(a['reward']);bl,bu=bounds(b['reward']);pairs.append(dict(key=key,lower=bl-au,upper=bu-al,actual_difference=None if a['reward']is None or b['reward']is None else b['reward']-a['reward'],identical_full_record=a['record']==b['record']))
 output=dict(status='PASS_ACTUAL_CHESS_REPLAY_AND_FINITE_CURVES',train_games=len(games),train_legal_plies=checks,evaluation_legal_plies=replayed_eval,curve_rows=len(curves),summaries=summaries,runner_reason_corrections=corrected,heldout_pairs=pairs,scope='Actual rules/legal records checked using same independent library rule authority. No external engine strength validation. Parameter motion/search-target counts are not strength. Search trace correctness separately exhaustively tested on toy trees.')
 (OUT/'audit.json').write_text(json.dumps(output,indent=2));print(json.dumps({k:v for k,v in output.items()if k not in('summaries','heldout_pairs')}))
if __name__=='__main__':run()
