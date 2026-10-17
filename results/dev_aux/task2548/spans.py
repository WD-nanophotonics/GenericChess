"""Exact integer-feature span of ACTUALLY admitted learning observations."""
from pathlib import Path
from fractions import Fraction
from collections import defaultdict,Counter
import json,time
D=Path('results/dev_aux/task2546');O=Path('results/dev_aux/task2548')
class Span:
 def __init__(self):self.rows={};self.observations=0;self.nonzero=0
 def add(self,phi):
  self.observations+=1;self.nonzero+=any(phi)
  if len(self.rows)==6:return
  v=list(map(Fraction,phi))
  for j in sorted(self.rows):
   a=v[j]
   if a:v=[x-a*y for x,y in zip(v,self.rows[j])]
  k=next((j for j,x in enumerate(v)if x),None)
  if k is not None:
   f=v[k];self.rows[k]=[x/f for x in v]
 def result(self):
  free=[j for j in range(6)if j not in self.rows];basis=[]
  for j in free:
   v=[Fraction(0)]*6;v[j]=1
   for k,row in sorted(self.rows.items(),reverse=True):v[k]=-sum(row[z]*v[z]for z in range(k+1,6))
   assert all(sum(a*b for a,b in zip(row,v))==0 for row in self.rows.values());basis.append(list(map(str,v)))
  return dict(rank=len(self.rows),rows=self.observations,nonzero=self.nonzero,nullspace=basis,echelon={str(k):list(map(str,v))for k,v in self.rows.items()})
def run():
 start=time.perf_counter();spans=defaultdict(Span);terms=Counter()
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if not q['observed']:continue
  gs=q['generator_seed'];m=q['method'];key=(gs,m)
  if not q['pv_terminal']:spans[key+('ordinary_PV',)].add(q['pv_phi'])
  if m=='TreeStrap':
   for s in q['samples']:spans[key+('admitted_interior',)].add(s['phi'])
  if m=='TD':terms[key]+=q['pv_terminal']
 invariant_checks=[];train=json.loads((D/'result.json').read_text())
 for a in train['arms']:
  name='ordinary_PV'if a['method']=='TD'else'admitted_interior';sp=spans[a['generator_seed'],a['method'],name].result()
  for n in sp['nullspace']:
   v=list(map(Fraction,n));before=sum(float(x)*w for x,w in zip(v,a['initial']));after=sum(float(x)*w for x,w in zip(v,a['weights']));error=abs(after-before);assert error<1e-9;invariant_checks.append(dict(rule=a['generator_seed'],method=a['method'],seed=a['seed'],null_vector=n,initial_component=before,final_component=after,absolute_error=error))
 out=dict(invariant_checks=invariant_checks,status='EXACT_FEATURE_SPANS_NOT_USEFULNESS_PROOF',rows=[dict(rule=g,method=m,source=k,**s.result())for(g,m,k),s in sorted(spans.items())],terminal_PV_constant_counts=[dict(rule=g,method=m,n=v)for(g,m),v in terms.items()],seconds=time.perf_counter()-start,scope='Exact Fraction row elimination over actual admittedintegerfeatures pooled acrossallinitials; not gradients/residualweighted excitation or rule-invariant proof. TerminalPVconstant no ordinaryinput. Fullrankdoesnotprove stableprices/WLDgain; lower rank may reflect visitedsupport, notuniversalruleidentity. Differentmethodvisitation/updates remainconfounded; no new query or fitness selection.')
 (O/'spans.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
