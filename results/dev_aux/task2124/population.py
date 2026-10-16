"""Exact population capacity from previously audited complete 3x3 Core graph."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,time,math,hashlib
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2117.capacity import regions
from results.dev_aux.task2096.capacity import counts
OUT=Path('results/dev_aux/task2124')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('original120cap neverrestart')
 start=time.perf_counter();deadline=start+120;p=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');source=Path('results/dev_aux/task2094/labels.jsonl');assert hashlib.sha256(source.read_bytes()).hexdigest()==p['pins'][str(source)];labels=[json.loads(x)for x in source.read_text().splitlines()];actor=RoyalActor(3);values={'WIN':1,'DRAW':0,'LOSS':-1};tot=Counter();ranks=Counter();results=[]
 def leaves(row):
  if row['status']!='ongoing':
   v=values[row['label']]*(1 if row['board'][-1]==0 else-1);return dict(terminal=0 if v==0 else math.inf if v==1 else-math.inf)
  return dict(coeff=counts(row['board'],0))
 def score(t,r):return t['terminal']if'terminal'in t else t['coeff'][0]*r+t['coeff'][1]
 for row in labels:
  if time.perf_counter()>=deadline:raise TimeoutError('original120cap')
  raw=tuple(row['board'])
  if row['inventory']!='KKBNbn'or raw[-1]!=0 or row['status']!='ongoing'or any(actor.attacked(raw,actor.king(raw,s),1-s)for s in(0,1)):continue
  actionleaves=[];lines=set();q={e['action']:-e['child_value']for e in row['actions']}
  for e in row['actions']:
   child=labels[e['child']]
   ll=[leaves(child)]if child['status']!='ongoing'else[leaves(labels[x['child']])for x in child['actions']]
   assert ll;lines.update(tuple(x['coeff'])for x in ll if'coeff'in x);actionleaves.append((e['action'],ll))
  points,reps=regions(lines);sets=[];firsts=[];anygood=[];allgood=[]
  # Independentpublicsortedactionorder fromserializedboardcoordinates.
  def order(name):
   return json.dumps(dict(kind='board',**{'from':[ord(name[0])-97,int(name[1])-1],'to':[ord(name[2])-97,int(name[3])-1]},promotion_target_id=None),sort_keys=True)
  actionleaves.sort(key=lambda pair:order(pair[0]))
  for ratio in reps:
   vv=[min(score(t,ratio)for t in ll)for _,ll in actionleaves];best=max(vv);aa=[a for(a,_),v in zip(actionleaves,vv)if v==best];sets.append(tuple(aa));firsts.append(aa[0]);anygood.append(any(q[a]==max(q.values())for a in aa));allgood.append(all(q[a]==max(q.values())for a in aa))
  rec=dict(index=row['index'],board=row['board'],positional_label=row['label'],rank=row['rank'],nonflat=len(set(q.values()))>1,price_sensitive_top_sets=len(set(sets))>1,price_sensitive_first=len(set(firsts))>1,no_positive_price_any_top_optimal=not any(anygood),no_positive_price_all_top_optimal=not any(allgood),no_positive_price_first_optimal=not any(q[a]==max(q.values())for a in firsts),positive_crossings=[str(x)for x in points]);results.append(rec);tot['roots']+=1;tot[row['label']]+=1
  for k in('nonflat','price_sensitive_top_sets','price_sensitive_first','no_positive_price_any_top_optimal','no_positive_price_all_top_optimal','no_positive_price_first_optimal'):tot[k]+=rec[k]
  if row['label']=='WIN':
   for horizon in(6,12,24):ranks['WIN_rank_at_most'+str(horizon)]+=row['rank']<=horizon
 (OUT/'population.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in results),encoding='utf-8');result=dict(status='COMPLETE_EXACT_3X3_STRUCTURAL_POPULATION_DEPTH2',counts=dict(tot),positive_rank_coverage=dict(ranks),seconds=time.perf_counter()-start,scope=p['interpretation'],no_DEV_read=True,no_new_training_or_game=True)
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
