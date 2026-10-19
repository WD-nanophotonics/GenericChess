"""Dot reply 1792413417.828509: per-arm paid nodes, valid TD terms, actual updates, games and time at
25k/50k/100k from EXISTING training logs (5x5 task2588 vs 4x4 cold arms task2587). No new training."""
from pathlib import Path
import json,collections
def table(task,method='Fixed',bounds=(25000,50000,100000)):
 G=Path(f'results/dev_aux/{task}/generic');res=json.loads((G/'result.json').read_text());rows=collections.defaultdict(list)
 for g in map(json.loads,(G/'games.jsonl').open()):
  if g['method']==method:rows[(g['generator_seed'],g['seed'])].append(g)
 out=[]
 for (gs,seed),gl in sorted(rows.items()):
  arm=next(a for a in res['arms']if a['generator_seed']==gs and a['seed']==seed and a['method']==method)
  for b in bounds:
   sub=[g for g in gl if g['total_nodes']<=b]
   out.append(dict(rule=gs,seed=seed,boundary=b,paid_nodes=sub[-1]['total_nodes']if sub else 0,games=len(sub),valid_TD_terms=sum(g['stats']['samples']for g in sub),actual_updates=sum(g['weights']!=g['initial_weights']for g in sub),terminal_games=sum(g['outcome']is not None for g in sub),mean_plies=sum(len(g['record']['actions'])-len(g['initial_record']['actions'])for g in sub)/max(1,len(sub))))
  out[-1]['arm_seconds']=arm['seconds']
 agg={}
 for b in bounds:
  r=[x for x in out if x['boundary']==b];agg[str(b)]={k:sum(x[k]for x in r)/len(r)for k in('paid_nodes','games','valid_TD_terms','actual_updates','terminal_games','mean_plies')}
 return dict(task=task,arms=len(rows),rows=out,mean_per_arm=agg,arm_seconds_mean=sum(a['seconds']for a in res['arms']if a['method']==method)/len(rows))
def run():
 res=dict(status='EXISTING_LOGS_ONLY',five_by_five=table('task2588'),four_by_four_cold_ref=table('task2587'),note='Exposure description only. Equal paid nodes is the registered budget currency (Dot); terms/updates are not independent-information counts and do not control sample quality.')
 Path('results/dev_aux/task2589/exposure-table.json').write_text(json.dumps(res,indent=2))
 for k in('five_by_five','four_by_four_cold_ref'):
  t=res[k];print(k,t['task'],'arms',t['arms'],'arm_seconds_mean',round(t['arm_seconds_mean'],1))
  for b,v in t['mean_per_arm'].items():print('  ',b,{x:round(y,1)for x,y in v.items()})
if __name__=='__main__':run()
