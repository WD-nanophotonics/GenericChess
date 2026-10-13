from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1080';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1077/plan.json').read_bytes());games=[json.loads(x) for x in (R/'results/dev_aux/task1079/games.jsonl').read_text().splitlines()];prices=plan['prices'];scores={p:F(sum((g['label']=='W')-(g['label']=='L') for g in games if g['price']==p),sum(g['price']==p for g in games)) for p in prices};traces=[]
for start in plan['starts']:
 cur=prices.index(start);path=[dict(price=prices[cur],reward=str(scores[prices[cur]]))]
 for iteration in range(6):
  ns=[i for i in [cur-1,cur+1] if 0<=i<len(prices) and scores[prices[i]]>scores[prices[cur]]]
  if not ns:break
  cur=sorted(ns,key=lambda i:(-scores[prices[i]],prices[i]))[0];path.append(dict(price=prices[cur],reward=str(scores[prices[cur]])))
 traces.append(dict(start=start,selected=prices[cur],trace=path))
out=dict(train_scores={p:str(s) for p,s in scores.items()},traces=traces,dev_prices=sorted(set([64,671,90]+[x['selected'] for x in traces])),selection_used_development=False,training_reward='actualW-L/N ALLgames C0 D0distinct, equalopp/color/familyweights',scope=plan['scope']);(O/'selection.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
