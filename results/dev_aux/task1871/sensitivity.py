"""Read completed independent material action sets; no additional search/labels."""
from pathlib import Path
from collections import defaultdict,Counter
import json,math
ROOT=Path('results/dev_aux/task1870');OUT=Path('results/dev_aux/task1871')
def score(x):return math.inf if x=='WIN_INFINITY' else -math.inf if x=='LOSS_INFINITY' else x
def run():
 done=json.loads((ROOT/'completion.json').read_text());p=json.loads((ROOT/'reference_plan.json').read_text());rows=[json.loads(x) for x in (ROOT/'roots.jsonl').read_text().splitlines()];assert done['status']=='COMPLETE' and len(rows)==192 and all(r['complete'] for r in rows)
 by=defaultdict(dict);ratios=(.5,1.,2.);nativegroups=Counter();scoped=[]
 for r in rows:
  values={a['move']:score(a['value']) for a in r['action_scores']};best=max(values.values());bestset=set(a for a,v in values.items() if v==best);by[r['state']][r['ratio']]=bestset
  native={n['profile']['scale']:n for n in r['native']};vals=[values[n['move']] for n in native.values()]
  if len({n['move'] for n in native.values()})>1:
   nativegroups['unit_changed']+=1;nativegroups['unit_changed_unequal_reference_values']+=len(set(vals))>1
  scoped.append(dict(state=r['state'],ratio=r['ratio'],best_moves=sorted(bestset),all_native_optimal=all(values[n['move']]==best for n in native.values()),native_optimal_by_scale={unit:values[n['move']]==best for unit,n in native.items()}))
 summary=[]
 for state,sets in sorted(by.items()):
  assert len(sets)==3
  intersection=set.intersection(*(sets[ratio] for ratio in ratios));union=set.union(*(sets[ratio] for ratio in ratios))
  summary.append(dict(state=state,common_optimal_moves=sorted(intersection),different_optimal_sets=len({tuple(sorted(x)) for x in sets.values()})>1,disjoint_between_low_high=not(sets[.5]&sets[2.]),all3_conflict=not intersection,best_by_ratio={ratio:sorted(sets[ratio]) for ratio in ratios}))
 result=dict(status='PASS_FULL_INPUT_GRID_PRICE_SENSITIVITY',states=len(by),state_ratio_cases=len(rows),reused=sum(r.get('reused',False) for r in rows),actual_new_reference_nodes=sum(r['nodes'] for r in rows),origin_reused_nodes=sum(r.get('origin_nodes',0) for r in rows),actual_new_reference_seconds=sum(r['seconds'] for r in rows),different_optimal_sets=sum(s['different_optimal_sets'] for s in summary),no_common_optimal_move_across3prices=sum(s['all3_conflict'] for s in summary),disjoint_low_high=sum(s['disjoint_between_low_high'] for s in summary),unit_changes=dict(nativegroups),states_detail=summary,native_scoped_quality=scoped,interpretation='This finite-depth material comparator is a signal/opportunity diagnostic only; no reward replacement, WDL guarantee, independent holdout, humanpricefit or Nativequiescence equivalence. Shared optimalmove means a price-independent action can satisfy all3finiteobjectives; different sets alone may only remove ties. No common move is a stronger finiteobjective conflict, still not actualW-L informativeness. All192inputs included,28paidresults reused with originwork not chargedtwice. No statistical unit chosen.')
 with (OUT/'report.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('states_detail','native_scoped_quality')}))
if __name__=='__main__':run()
