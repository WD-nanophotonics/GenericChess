"""ALL-coefficient cross-initialization dispersion and pair votes; descriptive."""
from pathlib import Path
from math import sqrt
import json,itertools
D=Path('results/dev_aux/task2580')
def run():
 p=json.loads((D/'plan.json').read_text());t=json.loads((D/'result.json').read_text());a={(x['seed'],x['method']):x for x in t['arms']};groups={}
 for method in ('initial','TD_early','TD_mixed'):
  rows=[]
  for seed in p['seeds']:
   x=a.get((seed,'TD_early'))if method=='initial'else a.get((seed,method))
   if x is not None:rows.append(dict(seed=seed,weights=x['initial']if method=='initial'else x['weights']))
  coeff=[]
  for j,name in enumerate(('P','N','B','R','Q')):
   vs=[r['weights'][j]for r in rows];mean=sum(vs)/max(1,len(vs));coeff.append(dict(piece=name,n=len(vs),mean=mean,min=min(vs)if vs else None,max=max(vs)if vs else None,rms_deviation=sqrt(sum((x-mean)**2 for x in vs)/max(1,len(vs)))))
  votes=[]
  for j,k in itertools.combinations(range(5),2):
   v=[dict(seed=r['seed'],sign=(r['weights'][j]>r['weights'][k])-(r['weights'][j]<r['weights'][k]),difference=r['weights'][j]-r['weights'][k])for r in rows];ss={x['sign']for x in v};votes.append(dict(pair=[('P','N','B','R','Q')[j],('P','N','B','R','Q')[k]],votes=v,unanimous=len(v)==4 and len(ss)==1,common_sign=next(iter(ss))if len(v)==4 and len(ss)==1 else None))
  groups[method]=dict(rows=rows,coefficients=coeff,all10pairs=votes,unanimous_pairs=sum(x['unanimous']for x in votes),total_pairs=10,full_order_unanimous=len(rows)==4 and len(set(tuple(sorted(range(5),key=lambda j:r['weights'][j]))for r in rows))==1)
 r=dict(status='ALL_INITIALS_COEFFICIENTS_AND_PAIRS_RETAINED',groups=groups,scope='TRAIN-only descriptive analysis prepared after trained weights were observed but before EVAL fitness inspection; all5coefficients/10pairs shown, no favorable pair/seed/price selection. Pfixed1 raw gauge; four seeds not population/statistical convergence or human ratio target. Snapshot drift/dispersion does not prove identifiability or playing strength.')
 (D/'stability.json').write_text(json.dumps(r,indent=2));print(json.dumps({m:dict(unanimous_pairs=g['unanimous_pairs'],full_order_unanimous=g['full_order_unanimous'])for m,g in groups.items()}))
if __name__=='__main__':run()
