from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1120';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1117/plan.json').read_bytes());games=[json.loads(x) for x in (R/'results/dev_aux/task1118/games.jsonl').read_text().splitlines()];prices=plan['prices'];arms=[]
for arm in ['J','L']:
 scores={p:F(sum((g['label']=='W')-(g['label']=='L') for g in games if g['arm']==arm and g['price']==p),sum(g['arm']==arm and g['price']==p for g in games)) for p in prices};globalprice=sorted(prices,key=lambda p:(-scores[p],p))[0];paths=[]
 for start in [64,671]:
  cur=prices.index(start);trace=[dict(price=prices[cur],score=str(scores[prices[cur]]))]
  for iteration in range(4):
   neighbors=[i for i in [cur-1,cur+1] if 0<=i<len(prices) and scores[prices[i]]>scores[prices[cur]]]
   if not neighbors:break
   cur=sorted(neighbors,key=lambda i:(-scores[prices[i]],prices[i]))[0];trace.append(dict(price=prices[cur],score=str(scores[prices[cur]])))
  paths.append(dict(start=start,selected=prices[cur],trace=trace))
 arms.append(dict(arm=arm,scores={p:str(v) for p,v in scores.items()},global_selected=globalprice,local_paths=paths))
result=dict(status='TRAIN_ONLY_FROZEN_GLOBAL_AND_NEIGHBOR_SELECTIONS',arms=arms,development_used=False,new_go=0,scope=plan['scope']);(O/'selection.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(arms)
