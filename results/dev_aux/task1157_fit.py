from pathlib import Path
from fractions import Fraction as F
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1157';O.mkdir(exist_ok=False);gs=[json.loads(x) for x in (R/'results/dev_aux/task1154/games.jsonl').read_text().splitlines()]
def row(g):
 d={t:sum(1 if c==g['color'] else -1 for t2,c in zip(g['root']['types'],g['root']['colors']) if t2==t) for t in [4,2]};return [F(d[4]),F(d[2]),F(g['opponent']=='uniform_random')],F((g['label']=='W')-(g['label']=='L'))
def fit(games,restricted=False):
 rr=[row(g) for g in games];rr=[([x[0]+x[1],x[2]],y) for x,y in rr] if restricted else rr;n=len(rr[0][0]);A=[[sum(x[i]*x[j] for x,y in rr) for j in range(n)]+[sum(x[i]*y for x,y in rr)] for i in range(n)]
 for j in range(n):
  pivot=next((i for i in range(j,n) if A[i][j]),None)
  if pivot is None:return None
  A[j],A[pivot]=A[pivot],A[j];v=A[j][j];A[j]=[a/v for a in A[j]]
  for i in range(n):
   if i!=j:v=A[i][j];A[i]=[a-v*b for a,b in zip(A[i],A[j])]
 return [A[i][-1] for i in range(n)]
train=[g for g in gs if g['root']['composition_ordinal']<4];dev=[g for g in gs if g['root']['composition_ordinal']>=4];coef=fit(train);base=fit(train,True);assert coef and base
def assess(games,b,restricted=False):
 vals=[]
 for g in games:
  x,y=row(g);x=[x[0]+x[1],x[2]] if restricted else x;p=sum(a*c for a,c in zip(x,b));vals.append((p-y)**2)
 return str(sum(vals)/len(vals))
positive=coef[0]>0 and coef[1]>0;ratio=coef[0]/coef[1] if positive else None;tableprice=round(720*ratio) if ratio else None;eligible=bool(positive and 1<=tableprice<=3328)
seeds={g['root']['seed'] for g in train};by={s:[g for g in train if g['root']['seed']==s] for s in seeds};groups=[[s for s in seeds if by[s][0]['root']['composition']==c] for c in sorted(set(g['root']['composition'] for g in train))];rng=random.Random(2026229000);samples=[];invalid=0
for _ in range(2000):
 xx=[g for group in groups for _ in group for g in by[rng.choice(group)]];b=fit(xx)
 if b and b[0]>0 and b[1]>0:samples.append(float(b[0]/b[1]))
 else:invalid+=1
samples.sort();conditional=[samples[int(.025*(len(samples)-1))],samples[int(.975*(len(samples)-1))]] if samples else None
result=dict(status='EXACT_TRAIN_ONLY_STATISTICAL_OUTCOME_MATERIAL_FIT',coefficients_R_N_random_offset=list(map(str,coef)),restricted_equalprice_coefficients=list(map(str,base)),train_N=len(train),dev_N=len(dev),train_MSE=assess(train,coef),dev_MSE=assess(dev,coef),restricted_train_MSE=assess(train,base,True),restricted_dev_MSE=assess(dev,base,True),positive_ratio=str(ratio) if ratio else None,normalized_table_R=tableprice,normalized_table_N=720,table_supported=eligible,bootstrap_replicates=2000,nonpositive_or_singular_bootstraps=invalid,conditional_positive_ratio_quantiles=conditional,scope='Countdifferencesareinputfeatures,actualW-Lislabel,C/Ddistinct0finiteevent. Predictivefixedpolicy/contactdistributionmarginalsNOTpolicyoptimalprices orintrinsic/universalwinprobabilities. Nohumanlabels/prior/signclipping. BootstrapconditionalquantilesnotunconditionalCI.',new_go=0)
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
