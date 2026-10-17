
"""Exact rational arrangement of two prespecified 1-D finite-search restrictions."""
from pathlib import Path
from fractions import Fraction as F
from math import inf
import json,hashlib,time
OUT=Path('results/dev_aux/task2473')
def solve(panel):
 folder=Path(f"results/dev_aux/task{panel['task']}")
 nodes=[json.loads(x)for x in(folder/'nodes.jsonl').read_text().splitlines()]
 assert json.loads((folder/'result.json').read_text())['status']=='COMPLETE'
 base=list(map(F,map(str,panel['base'])));direction=list(map(F,panel['direction']));low,high=map(lambda x:F(str(x)),panel['domain'])
 lines={}
 for n in nodes:
  fs=list(map(F,n['features']));constant=fs[-1]+sum(x*y for x,y in zip(fs,base));slope=sum(x*y for x,y in zip(fs,direction));lines[n['index']]=(constant,slope)
 unique=set(lines.values());cuts={low,high}
 for a,b in unique:
  for c,d in unique:
   if b!=d:
    q=(c-a)/(b-d)
    if low<q<high:cuts.add(q)
 cuts=sorted(cuts);pieces=[dict(kind='vertex',lo=q,hi=q,q=q)for q in cuts]+[dict(kind='open_interval',lo=a,hi=b,q=(a+b)/2)for a,b in zip(cuts,cuts[1:])]
 def fold(q):
  values={};leaves={}
  for i in range(len(nodes)-1,-1,-1):
   n=nodes[i]
   if n['status']!='ongoing':values[i]=0 if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf;leaves[i]=i
   elif n['depth_remaining']==0:values[i]=lines[i][0]+lines[i][1]*q;leaves[i]=i
   else:
    v=(max if n['side']==nodes[0]['side']else min)(values[j]for _,j in n['children']);j=next(j for _,j in n['children']if values[j]==v);values[i]=v;leaves[i]=leaves[j]
  actions=[dict(index=k,choice=ch,value=str(values[j]),leaf=leaves[j],affine=[str(x)for x in lines[leaves[j]]],features=nodes[leaves[j]]['features'],terminal=nodes[leaves[j]]['status']!='ongoing')for k,(ch,j)in enumerate(nodes[0]['children'])]
  best=max(values[j]for _,j in nodes[0]['children']);winners=[k for k,(_,j)in enumerate(nodes[0]['children'])if values[j]==best]
  return dict(chosen=winners[0],cooptimal=winners,score=str(best),actions=actions)
 rows=[]
 for piece in pieces:
  q=piece['q'];f=fold(q)
  # The complete ordering of every distinct affine leaf line is constant in an open cell.
  if piece['kind']=='open_interval':
   signatures=[]
   for point in((2*piece['lo']+piece['hi'])/3,(piece['lo']+2*piece['hi'])/3):
    ff=fold(point);assert ff['cooptimal']==f['cooptimal'] and ff['chosen']==f['chosen']
    signatures.append(ff['chosen'])
  rows.append({**{k:str(v)if isinstance(v,F)else v for k,v in piece.items()},**f})
 return dict(task=panel['task'],parameter=panel['parameter'],domain=panel['domain'],nodes=len(nodes),distinct_affine_lines=len(unique),cuts=[str(x)for x in cuts],pieces=rows)
def run():
 t=time.perf_counter();p=json.loads((OUT/'plan.json').read_text())
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
 panels=[solve(x)for x in p['panels']]
 r=dict(status='COMPLETE_EXACT_RATIONAL_LINE_ORDER_ARRANGEMENTS',panels=panels,seconds=time.perf_counter()-t,scope=p['scope']+' Verticesandopenintervals separately retainALLcooptimalrootactions; strictfirstlegalchoice. Finitevalue models exactintegerquartercoefficients, notallfloatinginputs. FullCoretrees independentlyreplayed elsewhere.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2))
 for pp in panels:
  print(json.dumps(dict(task=pp['task'],nodes=pp['nodes'],cuts=pp['cuts'],pieces=[dict(kind=x['kind'],lo=x['lo'],hi=x['hi'],chosen=x['chosen'],cooptimal=x['cooptimal'])for x in pp['pieces']])))
if __name__=='__main__':run()
