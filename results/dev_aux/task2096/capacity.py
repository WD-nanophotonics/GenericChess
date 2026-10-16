"""Exact positive-price-line capacity; no fitted selected price or policy gains."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,time,hashlib
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2096')
def counts(raw,target):
 return tuple(sum((1 if ch.isupper()else-1)*(1 if target==0 else-1)for ch in raw[:-1]if ch.upper()==tid)for tid in('N','B'))
def main():
 start=time.perf_counter();plan=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));path=Path(plan['teacher']);assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['teacher_sha'];labels=[json.loads(x)for x in path.read_text(encoding='utf-8').splitlines()];values={'WIN':1,'DRAW':0,'LOSS':-1};actor=RoyalActor(3);cases=[];breaks=set()
 for row in labels:
  if row['status']!='ongoing'or len(row['actions'])<2:continue
  q=[-values[labels[e['child']]['label']]for e in row['actions']]
  if min(q)==max(q):continue
  lines=[]
  for e in row['actions']:
   child=labels[e['child']]
   if child['status']=='ongoing':lines.append(counts(child['board'],row['board'][-1]))
   else:lines.append((0,0)if child['label']=='DRAW'else('WIN'if-values[child['label']]==1 else'LOSS',0))
  for i,(n,b)in enumerate(lines):
   for m,c in lines[i+1:]:
    if isinstance(n,int)and isinstance(m,int)and n!=m:
     crossing=Fraction(c-b,n-m)
     if crossing>0:breaks.add(crossing)
  board=row['board'];safe=all(not actor.attacked(tuple(board),actor.king(tuple(board),side),1-side)for side in(0,1));both=all(any(ch!='.'and ch.upper()!='K'and int(ch.islower())==side for ch in board[:-1])for side in(0,1));cases.append(dict(index=row['index'],board=board,inventory=row['inventory'],safe=safe,botharmed=both,lines=lines,q=q,actions=[e['action']for e in row['actions']]))
 bs=sorted(breaks);ratios=[];last=Fraction(0)
 for b in bs:ratios.extend([(last+b)/2,b]);last=b
 ratios.append(last+1);allmask=(1<<len(ratios))-1;intersection=allmask;witness=[];totals={str(r):dict(n=0,optimistic=0,pessimistic=0,tie_average=0.,alloptimal=0)for r in ratios};groups={g:Counter()for g in('all','botharmed','safe_fullBNbn')}
 for case in cases:
  mask=0;optimask=0
  for j,ratio in enumerate(ratios):
   scores=[float('inf')if n=='WIN'else-float('inf')if n=='LOSS'else n*ratio+b for n,b in case['lines']];best=max(scores);chosen=[i for i,s in enumerate(scores)if s==best];regret=[max(case['q'])-case['q'][i]for i in chosen];d=totals[str(ratio)];d['n']+=1;d['optimistic']+=min(regret);d['pessimistic']+=max(regret);d['tie_average']+=sum(regret)/len(regret);d['alloptimal']+=max(regret)==0
   if max(regret)==0:mask|=1<<j
   if min(regret)==0:optimask|=1<<j
  case['alloptimal_mask']=mask;case['anyoptimal_mask']=optimask
  new=intersection&mask
  if new!=intersection and len(witness)<8:witness.append(case.copy())
  intersection=new
  for name in('all',)+ (('botharmed',)if case['botharmed']else())+(('safe_fullBNbn',)if case['safe']and case['inventory']=='KKBNbn'else()):
   groups[name]['nonflat_roots']+=1;groups[name]['no_positive_ratio_all_top_optimal']+=mask==0;groups[name]['no_positive_ratio_any_top_optimal']+=optimask==0
 for d in totals.values():
  for k in('optimistic','pessimistic','tie_average','alloptimal'):d[k]/=d['n']
 result=dict(status='COMPLETE_EXACT_ALL_POSITIVE_RATIO_REGIONS',breakpoints=[str(x)for x in bs],representatives=[str(x)for x in ratios],groups={g:dict(c)for g,c in groups.items()},allroots_jointly_alloptimal_ratio_regions=intersection,per_region=totals,seconds=time.perf_counter()-start,scope=plan['scope'],counterexample='Greedynecessaryconstraintsubset, notminimumcardinality. Individualmask0alreadyshowsoneplymaterialcannotuniquelyrankgoodmoves; tiesexplicit.')
 assert result['seconds']<120
 (OUT/'counterexamples.json').write_text(json.dumps(witness,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
