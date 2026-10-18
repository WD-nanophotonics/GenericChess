"""Feature excitation diagnostic; rank is not external-target identifiability."""
from pathlib import Path
import json,sys
from math import tanh

def inverse_and_rank(a):
 n=len(a);m=[list(map(float,row))+[float(i==j)for j in range(n)]for i,row in enumerate(a)];scale=max([abs(v)for row in a for v in row]+[0.]);rank=0
 for col in range(n):
  pivot=max(range(rank,n),key=lambda i:abs(m[i][col]),default=None)
  if pivot is None or abs(m[pivot][col])<=max(1e-14,scale*1e-10):continue
  m[rank],m[pivot]=m[pivot],m[rank];v=m[rank][col];m[rank]=[x/v for x in m[rank]]
  for i in range(n):
   if i==rank:continue
   x=m[i][col];m[i]=[v-x*w for v,w in zip(m[i],m[rank])]
  rank+=1
 if rank<n:return rank,None
 inv=[row[n:]for row in m];condition=max(sum(map(abs,row))for row in a)*max(sum(map(abs,row))for row in inv);return rank,condition

def run(directory):
 d=Path(directory);by={}
 for q in map(json.loads,(d/'queries.jsonl').open()):
  if not q['observed']:continue
  key=str((q['seed'],q['method']));r=by.setdefault(key,dict(observations=0,material_PV=0,terminal_PV=0,nonzero_by_free_coordinate=[0]*4,raw_gram=[[0.]*4 for _ in range(4)],gradient_gram=[[0.]*4 for _ in range(4)]));r['observations']+=1;r['terminal_PV']+=q['pv_terminal']
  if q['pv_terminal']:continue
  r['material_PV']+=1;phi=q['pv_phi'][1:];factor=(1-tanh(q['value']/10.)**2)/10.
  for i in range(4):
   r['nonzero_by_free_coordinate'][i]+=phi[i]!=0
   for j in range(4):r['raw_gram'][i][j]+=phi[i]*phi[j];r['gradient_gram'][i][j]+=phi[i]*phi[j]*factor*factor
 for r in by.values():
  for field in ['raw_gram','gradient_gram']:
   rank,condition=inverse_and_rank(r[field]);r[field+'_rank']=rank;r[field+'_condition_inf']=condition
 result=dict(status='COMPLETE_DESCRIPTIVE_EXCITATION',by_arm=by,scope='AllobservedPVmaterialfeatures onactualTRAINtrajectories; fixedPexcluded. Four-coordinate Gram rank/infnormcondition describe localexcitation withrelativepivot1e-10, notuniqueprices/probabilitycalibration, causalexplanation or externaltrue-WDLidentifiability. No parameters/rootsselectedorupdated.')
 (d/'conditioning.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:dict(raw_rank=v['raw_gram_rank'],gradient_rank=v['gradient_gram_rank'],gradient_condition=v['gradient_gram_condition_inf'],nonzero=v['nonzero_by_free_coordinate'])for k,v in by.items()}))
if __name__=='__main__':run(sys.argv[1])
