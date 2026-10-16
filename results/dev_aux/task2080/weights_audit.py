"""Independent stdlib coefficients/residual/heldout-metric verification, no refit."""
from pathlib import Path
import json,hashlib,time
from scripts.generic_proof_rnb_bridge import orbit
OUT=Path('results/dev_aux/task2080')
def fv(raw):
 board=raw[:-1];turn=raw[-1];extra=[(i,p)for i,p in enumerate(board)if p not in('.','K','k')];owner=int(extra[0][1].islower())if extra else 0;own=board.index('k'if owner else'K');enemy=board.index('K'if owner else'k');relative=int(turn==owner);sign=1 if relative else-1
 data=[(0,sign*sum(p.upper()=='N'for _,p in extra)),(1,sign*sum(p.upper()=='B'for _,p in extra)),(2+relative*256+own*16+enemy,1)]
 for at,p in extra:data.append((514+relative*98+(0 if p.upper()=='N'else 49)+(at//4-own//4+3)*7+(at%4-own%4+3),1))
 return data

def verify(labels_path,models_path,expected,check_residual):
 labels=[json.loads(x)for x in Path(labels_path).read_text().splitlines()];models=json.loads(Path(models_path).read_text());stats={k:dict(n=0,sse=0.,absolute=0.,correct=0,gradient=[.01*x for x in w])for k,w in models.items()};ntrain=0;families={'TRAIN':set(),'DEV':set()}
 for l in labels:
  if l['status']!='ongoing':continue
  raw=tuple(l['board']);data=fv(raw);y={'WIN':1,'DRAW':0,'LOSS':-1}[l['label']];canonical=min(orbit(raw));f=hashlib.sha256(('2060:'+repr(canonical)).encode()).hexdigest();train=int(f,16)%4!=0;families['TRAIN'if train else'DEV'].add(f);ntrain+=train
  for name,w in models.items():
   pred=sum(w[i]*v for i,v in data);s=stats[name]
   if train:
    if check_residual:
     limit={'material':2,'kingking':514,'kingpiece':710}[name]
     for i,v in data:
      if i<limit:s['gradient'][i]+=(pred-y)*v
   else:s['n']+=1;s['sse']+=(pred-y)**2;s['absolute']+=abs(pred-y);s['correct']+=(1 if pred>.5 else-1 if pred<-.5 else 0)==y
 assert not families['TRAIN']&families['DEV'];results={}
 for name,s in stats.items():
  mse=s['sse']/s['n'];assert abs(mse-expected[name])<1e-11
  residual=max(abs(x)for x in s['gradient'])if check_residual else None
  if residual is not None:assert residual<1e-6
  results[name]=dict(DEV_n=s['n'],DEV_MSE=mse,DEV_accuracy=s['correct']/s['n'],normal_equation_max_residual=residual)
 return dict(TRAIN=ntrain,TRAIN_families=len(families['TRAIN']),DEV_families=len(families['DEV']),models=results)

def run():
 t=time.perf_counter();a=json.loads(Path('results/dev_aux/task2060/result.json').read_text());expected={k:v['DEV_MSE']for k,v in a['models'].items()};old=verify('results/dev_aux/task2058/labels.jsonl','results/dev_aux/task2060/models.json',expected,True)
 b=json.loads(Path('results/dev_aux/task2070/result.json').read_text());expected={r['model']:r['newDEV']['MSE']for r in b['models']};fresh=verify('results/dev_aux/task2065/labels.jsonl','results/dev_aux/task2070/models.json',expected,True)
 c=json.loads(Path('results/dev_aux/task2067/result.json').read_text());expected={r['model']:r['newDEV']['MSE']for r in c['curves']if r['method']=='ZERO_SHOT'};transfer=verify('results/dev_aux/task2065/labels.jsonl','results/dev_aux/task2060/models.json',expected,False)
 result=dict(status='PASS_STDLIB_INDEPENDENT_METRICS_AND_RIDGE_NORMAL_EQUATIONS',old_rule=old,new_rule_fullscratch=fresh,oldweights_on_newrule=transfer,seconds=time.perf_counter()-t,no_NumPy_or_fitting_or_search=True);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
