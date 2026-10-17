"""Descriptive coefficient-order agreement across ALL initializations, no human target."""
from pathlib import Path
from itertools import combinations
import json,time
T=Path('results/dev_aux/task2546');O=Path('results/dev_aux/task2548')
def run():
 began=time.perf_counter();tr=json.loads((T/'result.json').read_text());rows=[]
 for gs in sorted({a['generator_seed']for a in tr['arms']}):
  for method in('TD','TreeStrap'):
   aa=[a for a in tr['arms']if a['generator_seed']==gs and a['method']==method];pairs=[]
   for i,j in combinations(range(6),2):
    vals=[a['weights'][i]-a['weights'][j]for a in aa];signs=[(v>0)-(v<0)for v in vals];pairs.append(dict(coordinates=[i,j],signs=signs,all_agree=all(v==signs[0]and v!=0 for v in signs),min_abs_gap=min(abs(v)for v in vals)))
   rows.append(dict(rule=gs,method=method,initials=[a['seed']for a in aa],models=len(aa),pairwise_coordinate_orders=pairs,unanimous_nonzero_order_pairs=sum(r['all_agree']for r in pairs),total_coordinate_pairs=15,full_ordering_agrees=all(r['all_agree']for r in pairs)))
 out=dict(status='ALL_INIT_EXACT_ORDER_AGREEMENT_DESCRIPTIVE',rows=rows,seconds=time.perf_counter()-began,scope='Retrospective descriptive metric specified afterD2outcomes to answerpreexistinguserstable-ordergoal; not preregisteredhypothesis or populationtest. ALL4initials/raw6channelcoefficients, exactcomparison/NO margin; near-ties can be sensitive. No human ordering, selectedseed, normalizationdeployment, completepriceidentification or purealgorithmablation. Board-current and hand-base channels aredistinct contextualcoefficients.')
 (O/'orders.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],rows=[{k:r[k]for k in('rule','method','unanimous_nonzero_order_pairs','full_ordering_agrees')}for r in rows])))
if __name__=='__main__':run()
