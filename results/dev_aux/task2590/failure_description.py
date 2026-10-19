"""Existing-record description of the 363001 failure vs the 3 positive hybrid rules (no new games).
Absolute W/D/L/U of Cold@0 and Cold@100k per rule, initial->final weights per arm, TRAIN game length,
terminal share and TD terms per rule. Descriptive only."""
from pathlib import Path
import json,collections,statistics
D=Path('results/dev_aux/task2590')
CH=['board P','board A','board X','hand A','hand P','hand X']
def run():
 rows={tuple(g['slot']):g for g in map(json.loads,(D/'eval'/'eval-games.jsonl').open())};res=json.loads((D/'generic'/'result.json').read_text())
 absw=collections.defaultdict(collections.Counter)
 for s,g in rows.items():absw[(s[0],s[4])]['U'if g['reward']is None else'W'if g['reward']>0 else'L'if g['reward']<0 else'D']+=1
 train=collections.defaultdict(list)
 for g in map(json.loads,(D/'generic'/'games.jsonl').open()):train[g['generator_seed']].append(g)
 out={}
 for gs in sorted(train):
  arms=[a for a in res['arms']if a['generator_seed']==gs];gl=train[gs]
  out[str(gs)]=dict(eval_abs={m:dict(absw[(gs,m)])for m in('Cold@0','Cold@100k')},
   train_games=len(gl),train_terminal_share=sum(g['outcome']is not None for g in gl)/len(gl),train_mean_plies=statistics.mean(len(g['record']['actions'])-len(g['initial_record']['actions'])for g in gl),
   candidate_reward_mean=statistics.mean((g['outcome']*(1 if g['color']==0 else-1))for g in gl if g['outcome']is not None),
   terms=sum(g['stats']['samples']for g in gl),
   weights={str(a['seed']):dict(initial=[round(x,3)for x in a['initial']],final=[round(x,3)for x in a['weights']])for a in arms},
   mean_delta=[round(statistics.mean(a['weights'][j]-a['initial'][j]for a in arms),3)for j in range(6)])
 r=dict(status='DESCRIPTIVE_ONLY',channels=CH,rules=out);(D/'failure-description.json').write_text(json.dumps(r,indent=2))
 for gs,v in out.items():print(gs,'C0',v['eval_abs']['Cold@0'],'C100',v['eval_abs']['Cold@100k'],'| train games',v['train_games'],'term',round(v['train_terminal_share'],3),'plies',round(v['train_mean_plies'],1),'cand reward',round(v['candidate_reward_mean'],3),'| mean dW',v['mean_delta'])
if __name__=='__main__':run()
