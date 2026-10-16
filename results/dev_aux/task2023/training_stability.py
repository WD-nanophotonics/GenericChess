"""Post-lock TRAIN-only uncertainty; never changes chosen prices or DEV."""
from pathlib import Path
from collections import Counter
import json,random,hashlib
OUT=Path('results/dev_aux/task2023')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def rows(p):return[json.loads(x)for x in Path(p).read_text(encoding='utf-8').splitlines()]
def one(folder,key,n,opponents,seed):
 p=load(folder/'run-plan.json');data=rows(folder/'games.jsonl')[:p['train_games']];assert len(data)==p['train_games'] and all(x['phase']=='TRAIN' and x['outcome']!='UNKNOWN'for x in data)
 grid=p['prices'];values={r:[sum(g['finite_event_score']for g in data if g['family']==f and g[key]==r)/2 for f in range(n)] for r in grid}
 lock=load(folder/'FULL-lock-before-dev.json');assert lock['selected_'+key]==min(grid,key=lambda r:(-sum(values[r]),r))
 rng=random.Random(seed);selected=Counter();ties=Counter();strict=Counter();included=Counter()
 groups=[[f for f in range(n)if p['train_opponent_R'][f]==opp] for opp in opponents] if key=='R' else [list(range(n))]
 assert sum(map(len,groups))==n and all(groups)
 for _ in range(10000):
  sample=[group[rng.randrange(len(group))] for group in groups for _ in group];scores={r:sum(values[r][f]for f in sample) for r in grid};best=max(scores.values());maximizers=[r for r in grid if scores[r]==best];selected[min(maximizers)]+=1;ties[len(maximizers)]+=1;included.update(maximizers)
  if len(maximizers)==1:strict[maximizers[0]]+=1
 leave=[]
 for omitted in range(n):
  scores={r:sum(v for f,v in enumerate(values[r])if f!=omitted)for r in grid};best=max(scores.values());leave.append(dict(omitted=omitted,maximizers=[r for r in grid if scores[r]==best]))
 signatures={r:hashlib.sha256(json.dumps([g['record']['actions']for g in data if g[key]==r],sort_keys=True).encode()).hexdigest()for r in grid}
 return dict(status='TRAIN_ONLY_POSTLOCK_NO_NEW_LEARNING',folder=folder.as_posix(),parameter=key,grid=grid,selected=lock['selected_'+key],family_values=values,bootstrap10000_selected_frequency=dict(selected),bootstrap_tie_count_frequency=dict(ties),bootstrap_strict_unique_selected_frequency=dict(strict),bootstrap_maximizer_inclusion_frequency=dict(included),leave_one_family_maximizers=leave,unique_complete_trajectory_signatures=len(set(signatures.values())),scope='Uncertainty diagnostic of same TRAIN sample, not independent learners or newDEV. Stratified fixedopponent family bootstrap forKRN; ordinary family bootstrap forBfixedfoe. Scores/price locks never changed; observed action changes not gains. Numeric tie-break frequency alone is not identification: strict-unique and maximizer inclusion frequencies are separately reported.')
def run():
 a=one(Path('results/dev_aux/task2016'),'R',16,[360,720,1440,2880],20261016682023)
 b=one(Path('results/dev_aux/task2020'),'B',8,[1260],20261016682024) if Path('results/dev_aux/task2020/FULL-lock-before-dev.json').exists() else dict(status='INCOMPLETE_TRAIN_NO_SELECTOR',scope='Original cap retained; no stability inference from missing training cells.')
 d=dict(status='PASS_TRAIN_ONLY_UNCERTAINTY',KRN=a,KRNB=b)
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(d,f,indent=2)
 print(json.dumps({k:{x:v for x,v in y.items()if x in ('selected','bootstrap10000_selected_frequency','unique_complete_trajectory_signatures')}for k,y in d.items()if isinstance(y,dict)}))
if __name__=='__main__':run()
