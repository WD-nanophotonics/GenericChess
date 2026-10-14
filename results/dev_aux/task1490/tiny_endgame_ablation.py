from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1518';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));original=json.loads((G/'values.json').read_bytes());v=original['value'];rank=original['rank'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').read_text().splitlines()]
policy={p:{} for p in [720,1728]}
for line in (R/'results/dev_aux/task1507/choices.jsonl').open():
 x=json.loads(line);policy[x['leafR']][x['state_id']]=x['child_id']
changes=collections.Counter();rows=[]
for p,dd in policy.items():
 for sid,s in enumerate(states):
  if sum(z!=9 for z in s[:6])>3 or not edges[sid]:continue
  optimal=[(u,j) for u,j in edges[sid] if -v[j]==v[sid]]
  if v[sid]==1:u,j=min(optimal,key=lambda a:(rank[a[1]],a[0]));assert rank[j]<rank[sid]
  elif v[sid]==-1:u,j=min(optimal,key=lambda a:(-rank[a[1]],a[0]))
  else:u,j=min(optimal)
  changes[p]+=j!=dd[sid];rows.append({'state_id':sid,'leafR':p,'node_budget':16,'move':u,'child_id':j,'basis':'PRICE_INDEPENDENT_EXACT_ORACLE_ENDGAME_MAX3ACTORS','new_go':0});dd[sid]=j
plan={'question':'Are unrealized wins mainly a price-independent bare-piece endgame progress problem?','intervention':'Both prices same exact-rule oracle finisher only when totalactors<=3; no humanprices, no engine/productchange, no parameterrefit. Winningoracle uses strictlydecreasing mate rank; drawoptimal action accepted as set thenlex; losingdelaylargest rank.','scope':'Engineering attribution ablation of compositepolicy, NOT puremature pricelearning success. Opponent remains ALLlegal perfectbestresponse. Fixedactorcount threshold before evaluating resulting WDL.','changed_edges':dict(changes),'new_go':0};(O/'plan.json').write_text(json.dumps(plan,indent=2))
# Create separate derived-policy artifact with explicit intervention, preserving original raw actual queries.
with (O/'choices.jsonl').open('w') as f:
 for p,dd in policy.items():
  replacement={x['state_id']:x for x in rows if x['leafR']==p}
  for sid,j in dd.items():
   if sid in replacement:x=replacement[sid]
   else:x={'state_id':sid,'leafR':p,'node_budget':16,'move':next((u for u,k in edges[sid] if k==j),None),'child_id':j,'basis':'INHERITED_ACTUAL_COLD_MATURE_OR_FORCED_POLICY_FROM1507','new_go':0}
   f.write(json.dumps(x)+'\n')
(O/'result.json').write_text(json.dumps({'status':'COMPLETE','all_owned_engines_closed':True,'scope':plan['scope'],'actual_go':0},indent=2));print(plan)
