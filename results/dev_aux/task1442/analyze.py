from pathlib import Path
import json,collections,random
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1449';O.mkdir(exist_ok=False);allg={n:[json.loads(x) for x in (R/f'results/dev_aux/task{t}/games.jsonl').read_text().splitlines()] for n,t in [(512,1445),(4096,1446)]}
key=lambda g:(g['root']['seed'],g['color'],g['opponent']);by={n:{p:{key(g):g for g in gs if g['leafR']==p} for p in [720,1728,3407]} for n,gs in allg.items()};seeds=sorted({k[0] for k in by[512][720]});assert len(seeds)==64;y=lambda g:F((g['label']=='W')-(g['label']=='L'));rows=[];cache={}
for n in [512,4096]:
 for p,q,tag in [(3407,720,'TRAIN_SELECTED_MINUS_UNIFORM'),(1728,720,'FIXED_PRIOR_MINUS_UNIFORM'),(3407,1728,'TRAIN_SELECTED_MINUS_PRIOR')]:
  for ws in ['0','1/2','1']:
   w=F(ws);fd={s:sum((w if opp=='unit_search' else 1-w)*sum(y(by[n][p][s,c,opp])-y(by[n][q][s,c,opp]) for c in [False,True])/2 for opp in ['unit_search','uniform_random']) for s in seeds};cache[n,p,q,ws]=fd;v=list(map(float,fd.values()));rng=random.Random(2026539501);bs=sorted(sum(rng.choices(v,k=64))/64 for _ in range(5000))
   rows.append(dict(nodes=n,comparison=tag,weight=ws,mean=str(sum(fd.values())/64),bootstrap95=[bs[124],bs[4874]],family_deltas={s:str(x) for s,x in fd.items()}))
interaction=[]
for p,q in [(3407,720),(1728,720),(3407,1728)]:
 fd={s:cache[4096,p,q,'1/2'][s]-cache[512,p,q,'1/2'][s] for s in seeds};v=list(map(float,fd.values()));rng=random.Random(2026539501);bs=sorted(sum(rng.choices(v,k=64))/64 for _ in range(5000));interaction.append(dict(comparison=f'{p}-{q}:gain4096-minus512',mean=str(sum(fd.values())/64),bootstrap95=[bs[124],bs[4874]],family_deltas={s:str(x) for s,x in fd.items()}))
counts={n:{p:{opp:dict(collections.Counter(g['label'] for g in gs if g['leafR']==p and g['opponent']==opp)) for opp in ['unit_search','uniform_random']} for p in [720,1728,3407]} for n,gs in allg.items()}
out=dict(status='FROZEN_64DEV_LOW_NODE_PRICE_LEARNING_AND_HIGH_NODE_BRIDGE',primary='TRAINselected3407vsuniform720 at512mixed',rows=rows,paired_budget_gain_differences=interaction,counts=counts,new_go=0,scope='Oneprimarylowbudget; allhigherbudget/oldprior/subgroupssecondary. Bothteacher/candidatebudgetchanges so notonlycandidatecausal. TRAIN32winnerR/N3407/720 nothumanrestore/uniqueprice; keeplownegativeuncertain, no DEVfitting/extensionuntilsignificant. ActualH48 W-L,Dactual,Cunknown.')
(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='family_deltas'} for x in rows if x['weight']=='1/2']);print([{k:v for k,v in x.items() if k!='family_deltas'} for x in interaction])
