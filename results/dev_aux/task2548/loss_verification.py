"""Real completed-query one-sided loss derivatives against recorded updates."""
from pathlib import Path
from math import tanh,isclose
import json,time
D=Path('results/dev_aux/task2548');T=Path('results/dev_aux/task2546')
def run():
 start=time.perf_counter();p=json.loads((T/'plan.json').read_text());sel=json.loads((D/'search-verification.json').read_text());ids={(r['gameid'],r['ply'])for r in sel['rows']if r['key'][1]=='TreeStrap'};rows=[]
 for line in(T/'queries.jsonl').open():
  q=json.loads(line)
  if(q['gameid'],q['ply'])not in ids:continue
  assert q['observed']and q['method']=='TreeStrap'and q['complete'];ss=q['samples'];w=q['weights']
  def loss(v):
   total=0.
   for s in ss:
    pred=tanh(sum(a*b for a,b in zip(v,s['phi']))/10);lo=tanh(float(s['lower'])/10);hi=tanh(float(s['upper'])/10);e=lo-pred if pred<lo else hi-pred if pred>hi else 0.;total+=e*e/2
   return total/len(ss)
  assert isclose(loss(w),q['learning']['loss'],abs_tol=1e-12);h=1e-5;errs=[]
  for j in range(6):
   a=list(w);b=list(w);a[j]+=h;b[j]-=h;grad=(loss(a)-loss(b))/(2*h);expected=w[j]-p['eta']*grad;errs.append(abs(q['weights_after'][j]-expected))
  assert max(errs)<2e-8;rows.append(dict(gameid=q['gameid'],ply=q['ply'],rule=q['generator_seed'],seed=q['seed'],color=q['color'],samples=len(ss),loss=loss(w),maximum_weight_error=max(errs)))
 assert len(rows)==len(ids)
 out=dict(status='PASS_ACTUAL_COMPLETE_QUERY_FIXED_BOUND_MEAN_LOSS_DERIVATIVES',expected=32,available=len(ids),verified=len(rows),max_weight_error=max(r['maximum_weight_error']for r in rows),finite_difference_step=1e-5,rows=rows,seconds=time.perf_counter()-start,scope='AllTreeStrapqueries selected by pre-registered64-query searchaudit, no value/outcome selection. Truecentral finite difference of mean transformed one-sided loss with bounds frozen, comparedagainst actualstoredall6updates. No analyticModel.gradient/TreeStrap.update call or newsearch. Semigradientfit only, not actualWDLgradient/price deployment.')
 (D/'loss-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
if __name__=='__main__':run()
