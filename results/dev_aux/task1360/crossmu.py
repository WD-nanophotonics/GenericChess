from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1373';O.mkdir()
gs=[json.loads(v) for v in (R/'results/dev_aux/task1361/games.jsonl').read_text().splitlines()];key=lambda g:(g['root']['seed'],g['color'],g['opponent']);old={key(g):g for g in gs if g['price']==1440};new={key(g):g for g in gs if g['price']==1728};seeds=sorted({k[0] for k in old})
y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[]
for ws in ['0','1/2','1']:
 w=F(ws);fd={s:sum((w if o=='unit_search' else 1-w)*sum(y(new[s,c,o])-y(old[s,c,o]) for c in [False,True])/2 for o in ['unit_search','uniform_random']) for s in seeds};mean=sum(fd.values())/64;rng=random.Random(2026439500);values=[float(x) for x in fd.values()];boot=sorted(sum(rng.choices(values,k=64))/64 for _ in range(5000));rows.append(dict(weight=ws,new_minus_old=str(mean),bootstrap95=[boot[124],boot[4874]]))
# A rootturn choice is independent of opponent; count unique rootchoices once.
roots=[]
for s in seeds:
 matches=[k for k in old if k[0]==s and old[k]['color']==old[k]['actions'][0]['actor'] and k[2]=='unit_search'];assert len(matches)==1;k=matches[0]
 roots.append(dict(seed=s,old_first=old[k]['actions'][0]['move'],new_first=new[k]['actions'][0]['move'],changed=old[k]['actions'][0]['move']!=new[k]['actions'][0]['move']))
out=dict(status='OLD_FILTERED_TRAIN_RATIO2_VS_NEW_UNFILTERED_TRAIN_RATIO2P4_SAME_DEV',rows=rows,root_choices=roots,changed_rootchoices=sum(r['changed'] for r in roots),root_count=64,new_go=0,scope='Postresult pairedcontrast suggested byDot, candidateprices were frozen beforeDEV. Same-mu A/B stability is sampling not cross-mu. C unresolved; overlap of marginal CIs never substitutes this directpaired difference; no DEV choice.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(rows,'changed',out['changed_rootchoices'])
