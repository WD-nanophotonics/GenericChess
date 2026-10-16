"""Independent stdlib pair-basis metrics and fitted normal-equation checks."""
from pathlib import Path
from collections import Counter
import json,hashlib,itertools,time
from scripts.generic_proof_rnb_bridge import orbit
from results.dev_aux.task2080.weights_audit import fv
OUT=Path('results/dev_aux/task2085')
def run():
 start=time.perf_counter();models=json.loads(Path('results/dev_aux/task2082/models.json').read_text());expected=json.loads(Path('results/dev_aux/task2082/result.json').read_text());stats={k:dict(n=0,sse=0.,correct=0,gradient=[.01*x for x in w])for k,w in models.items()};nt=0;nd=0
 for line in Path('results/dev_aux/task2073/labels.jsonl').read_text().splitlines():
  l=json.loads(line)
  if l['status']!='ongoing':continue
  raw=tuple(l['board']);data=fv(raw);counts=Counter((int(x.islower()),x.upper())for x in raw[:-1]if x!='.');turn=raw[-1]
  for k,(a,b)in enumerate(itertools.combinations_with_replacement(('R','N','B'),2)):
   v=0
   for side in(0,1):
    n=counts[side,a];m=counts[side,b];v+=(1 if side==turn else -1)*(n*(n-1)/2 if a==b else n*m)
   data.append((710+k,v))
  family=hashlib.sha256(('2060:'+repr(min(orbit(raw)))).encode()).hexdigest();train=int(family,16)%4!=0;nt+=train;nd+=not train;y={'WIN':1,'DRAW':0,'LOSS':-1}[l['label']]
  for name,w in models.items():
   s=stats[name];prediction=sum(w[i]*v for i,v in data);base=name.replace('_pairs','');limit={'material':2,'kingking':514,'kingpiece':710}[base]
   if train:
    for i,v in data:
     if i<limit or(name.endswith('_pairs')and i>=710):s['gradient'][i]+=(prediction-y)*v
   else:s['n']+=1;s['sse']+=(prediction-y)**2;s['correct']+=(1 if prediction>.5 else -1 if prediction<-.5 else 0)==y
 result={}
 for name,s in stats.items():
  mse=s['sse']/s['n'];residual=max(abs(x)for x in s['gradient']);assert abs(mse-expected['models'][name]['DEV_MSE'])<1e-11 and residual<1e-6;result[name]=dict(MSE=mse,accuracy=s['correct']/s['n'],normal_equation_max_residual=residual)
 assert nt==146520 and nd==48832
 summary=dict(status='PASS_INDEPENDENT_ALL_SIX_PAIR_BASIS_METRICS',TRAIN=nt,DEV=nd,models=result,seconds=time.perf_counter()-start,no_NumPy_refit_or_search=True);(OUT/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':run()
