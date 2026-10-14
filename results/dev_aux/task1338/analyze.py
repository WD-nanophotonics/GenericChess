from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1341';O.mkdir()
old=[json.loads(v) for v in (R/'results/dev_aux/task1329/games.jsonl').read_text().splitlines()]
new=[json.loads(v) for v in (R/'results/dev_aux/task1339/games.jsonl').read_text().splitlines()]
key=lambda g:(g['root']['seed'],g['color'],g['opponent'])
maps={a:{key(g):g for g in old if g['arm']==a and g['color']==g['actions'][0]['actor']} for a in ['B','L']}
newmaps={p:{key(g):g for g in new if g['profile']==p} for p in ['baseline','L_first']}
y=lambda g:F((g['label']=='W')-(g['label']=='L'))
rows=[]
for opp in ['unit_search','uniform_random','mixed']:
 kk=[k for k in maps['B'] if opp=='mixed' or k[2]==opp]
 first=sum(y(newmaps['L_first'][k])-y(maps['B'][k]) for k in kk)/len(kk)
 full=sum(y(maps['L'][k])-y(maps['B'][k]) for k in kk)/len(kk)
 rows.append(dict(opponent=opp,N=len(kk),first_only=str(first),full_policy=str(full),remainder=str(full-first),changed_first=sum(maps['L'][k]['actions'][0]['move']!=maps['B'][k]['actions'][0]['move'] for k in kk),first_transitions=dict(collections.Counter(maps['B'][k]['label']+'>'+newmaps['L_first'][k]['label'] for k in kk)),full_transitions=dict(collections.Counter(maps['B'][k]['label']+'>'+maps['L'][k]['label'] for k in kk))))
(O/'result.json').write_text(json.dumps(dict(status='ROOTTURN_FIRST_VS_FULL_POLICY',rows=rows,scope='Exposed64rootturn subset, baseline commonprefill exact; remainder includes continuation and TT, not pure leaf causal effect',new_go=0),indent=2));print(rows)
