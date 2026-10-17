"""PRIMARY outcome-only interval arithmetic on exact published92 frozen records."""
from pathlib import Path
from collections import defaultdict
import sys,json,time
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/paid-td-20261017';O=D/'exact/results/dev_aux';started=time.perf_counter()
def bounds(pairs):
 lo=hi=0
 for a,b in pairs:
  av=(-1,1)if a['reward']is None else(a['reward'],a['reward']);bv=(-1,1)if b['reward']is None else(b['reward'],b['reward']);lo+=av[0]-bv[1];hi+=av[1]-bv[0]
 return [lo/len(pairs),hi/len(pairs)]
games=[json.loads(x)for x in (O/'task2540/games.jsonl').open()];by={tuple(g['slot']):g for g in games};p=json.loads((O/'task2540/plan.json').read_bytes());rows=[]
for g in games:assert g['reward']==(None if g['outcome']is None else g['outcome']*(1 if g['color']==0 else -1))
for foe in p['opponents']:
 for left,right in [('TD','initial'),('WDL','initial'),('TD','WDL')]:
  pairs=[(by[g,seed,f,c,left,foe],by[g,seed,f,c,right,foe])for g in p['generator_seeds']for seed in p['initial_seeds']for f in p['families']for c in (0,1)]
  assert all(a['initial_record']==b['initial_record']for a,b in pairs)
  rows.append(dict(foe=foe,comparison=left+'-'+right,pairs=len(pairs),bounds=bounds(pairs),by_role={str(c):bounds([(a,b)for a,b in pairs if a['color']==c])for c in (0,1)},by_seed={str(seed):bounds([(a,b)for a,b in pairs if a['seed']==seed])for seed in p['initial_seeds']}))
follow=[json.loads(x)for x in (O/'task2544/games.jsonl').open()];print('FOLLOW_KEYS',list(follow[0]));followrows=[]
for length in [4,5]:
 for foe in p['opponents']:
  for color in [0,1]:
   groups=defaultdict(dict)
   for g in follow:
    if g['foe']!=foe or g['color']!=color or g.get('prefix_length',g.get('prefix_plies'))!=length:continue
    groups[g['generator_seed'],g['seed'],g['family']][g['treatment']]=g
   pairs=[(r['TD'],r['WDL'])for r in groups.values()];assert pairs,(length,foe,color)
   followrows.append(dict(prefix=length,foe=foe,color=color,pairs=len(pairs),bounds=bounds(pairs)))
train=json.loads((O/'task2539/result.json').read_bytes());unchanged=[a for a in train['arms']if a['weights']==a['initial']];n=0
for a in unchanged:
 for f in p['families']:
  for color in (0,1):
   for foe in p['opponents']:
    x=by[a['generator_seed'],a['seed'],f,color,a['method'],foe];y=by[a['generator_seed'],a['seed'],f,color,'initial',foe];assert x['record']==y['record']and x['reward']==y['reward'];n+=1
assert len(unchanged)==6 and n==192
write_json(D/'independent-paired.json',dict(status='PASS_PRIMARY_ALL1536_OUTCOME_AND_ADAPTIVE_STRATA_BOUNDS',source_sha='3792d83068d5d0e61a0a33ebbf6850b414202c6f',original_games=len(games),original_unknown=sum(g['reward']is None for g in games),contrasts=rows,adaptive_games=len(follow),adaptive_unknown=sum(g['reward']is None for g in follow),adaptive_TD_minus_WDL_role_cells=followrows,unchanged_models=6,unchanged_fullrecords_and_rewards=192,seconds=time.perf_counter()-started,scope='PRIMARY math-only candidate-role sign/actualreward/U[-1,+1]/initialrecord pair checks. Adaptivefollowup keptseparate, no pooling/refit/causalcolor orsharedcriticbugclaim; ownerCorefullrecord/audit reproduction is separate source execution, not an externalrulesengine. Crossedpopulationenvelopes stillinclude0; no populationmethodwinner.'))
for r in rows:print(r['foe'],r['comparison'],r['bounds'])
for r in followrows:print('FOLLOW',r)
