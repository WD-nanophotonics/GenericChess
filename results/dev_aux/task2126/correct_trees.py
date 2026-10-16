from pathlib import Path
from fractions import Fraction
from collections import Counter,defaultdict
import json,time,hashlib
from results.dev_aux.task2117.capacity import regions,value
OUT=Path('results/dev_aux/task2126')
def corrected(tree):
 lines={(0,0)}
 def collect(t):
  if'coeff'in t:lines.add(tuple(t['coeff']))
  elif'edges'in t:
   for _,child in t['edges']:collect(child)
 collect(tree);points,reps=regions(lines);out=[]
 for r in reps:
  vv=[value(t,r)for _,t in tree['edges']];best=max(vv);aa=[name for(name,_),v in zip(tree['edges'],vv)if v==best];out.append(dict(ratio=str(r),top_actions=aa,first_action=aa[0]))
 return [str(x)for x in points],out

def run():
 start=time.perf_counter();old=[json.loads(x)for x in Path('results/dev_aux/task2117/queries.jsonl').read_text().splitlines()];rows=[];changed=[];groups={}
 for line,row in zip(Path('results/dev_aux/task2117/trees.jsonl').open(),old):
  tree=json.loads(line)['tree'];points,rs=corrected(tree);q=row['child_values'];best=max(q.values())
  for r in rs:
   regrets=[best-q[a]for a in r['top_actions']];r.update(any_top_position_optimal=min(regrets)==0,all_top_position_optimal=max(regrets)==0,optimistic_regret=min(regrets),pessimistic_regret=max(regrets))
  new=dict(row,breakpoints=points,regions=rs,distinct_top_sets=len({tuple(r['top_actions'])for r in rs}),distinct_first_actions=len({r['first_action']for r in rs}),no_ratio_any_top_optimal=not any(r['any_top_position_optimal']for r in rs),no_ratio_all_top_optimal=not any(r['all_top_position_optimal']for r in rs));rows.append(new)
  if any(new[k]!=row[k]for k in('breakpoints','distinct_top_sets','distinct_first_actions','no_ratio_any_top_optimal','no_ratio_all_top_optimal')):changed.append(dict(case=row['case'],depth=row['depth'],old_breakpoints=row['breakpoints'],new_breakpoints=points,old_first_choices=row['distinct_first_actions'],new_first_choices=new['distinct_first_actions']))
 for kind in('INITIAL','POSTTRIGGER_B_AND_N'):
  for depth in(1,2,3):
   rr=[r for r in rows if r['kind']==kind and r['depth']==depth];groups[kind+'_depth'+str(depth)]=dict(cases=len(rr),nonflat=sum(r['nonflat_child_position_WDL']for r in rr),price_changes_top_sets=sum(r['distinct_top_sets']>1 for r in rr),price_changes_first_action=sum(r['distinct_first_actions']>1 for r in rr),no_price_any_optimal=sum(r['no_ratio_any_top_optimal']for r in rr),no_price_all_optimal=sum(r['no_ratio_all_top_optimal']for r in rr),no_price_first_optimal=sum(not any(r['child_values'][x['first_action']]==max(r['child_values'].values())for x in r['regions'])for r in rr))
 (OUT/'queries-corrected.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rows),encoding='utf-8');result=dict(status='CORRECTED_ALL168_EXISTING_TREES_WITH_ACTUAL_DRAW_ZERO_LINE',queries=len(rows),groups=groups,changed_partition_receipts=changed,seconds=time.perf_counter()-start,new_Core_tree_or_fitness_queries=0,scope='Originaltreesandallconditionsretained; constantDRAWlineaddedasoverapprox, canintroduceredundantvalidregions. Existing2119public14180nodevalidationvalid; itsregioncompletenessclaimsuperseded. Global64inventorytheoremunaffected.')
 (OUT/'tree-correction.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
