"""Descriptive complete-ranking ceiling, not fitted/deployed prices.
Question declared before arithmetic: can top-choice saturation hide remaining
fixed-ranking headroom? Use ALL64pairs and original context-first weighting for
both immediate/reply tasks. Enumerate every strict type order (24 or120/rule),
verify the order of weighted task means attains minimum total pair loss. No
trajectory, action execution, coefficient selection or generalization claim.
"""
from pathlib import Path
from fractions import Fraction as F
from itertools import permutations
import json,hashlib,sys
sys.path.insert(0,str(Path.cwd()))
from scripts.research_record import write_record
p=Path(__file__).parent;report=dict(scope=__doc__,rules=[],inputs={})
for filename in ('pair-audit.json','reply-pair-audit.json'):
 d=json.loads((p/filename).read_bytes());report['inputs'][filename]=hashlib.sha256((p/filename).read_bytes()).hexdigest()
 for rule in d['rules']:
  pairs=rule['pairs'];types=sorted({t for r in pairs for t in r['pair']});losses={};means={}
  for r in pairs:
   a,b=r['pair'];bg=r['backgrounds'];means[a]=sum((F(x['mean_a']) for x in bg),F())/len(bg);means[b]=sum((F(x['mean_b']) for x in bg),F())/len(bg)
  for order in permutations(types):
   rank={t:i for i,t in enumerate(order)};loss=F()
   for r in pairs:
    a,b=r['pair'];oracle=sum((F(x['oracle']) for x in r['backgrounds']),F())/len(r['backgrounds']);loss+=oracle-(means[a] if rank[a]<rank[b] else means[b])
   losses[order]=loss/len(pairs)
  best=min(losses.values());sorted_order=tuple(sorted(types,key=lambda t:(-means[t],t)));assert losses[sorted_order]==best
  fixed={n:sum((F(r['losses'][n]) for r in pairs),F())/len(pairs) for n in ('generic_v2','semantic_v3')}
  # Mean-based pair ceilings must be simultaneously attainable by one order.
  pairwise=sum((sum((F(x['oracle']) for x in r['backgrounds']),F())/len(r['backgrounds'])-max(means[t] for t in r['pair']) for r in pairs),F())/len(pairs);assert pairwise==best
  row=dict(task='immediate' if filename=='pair-audit.json' else 'one_reply',seed=rule['seed'],types=types,permutations=len(losses),fixed_losses=fixed,best_ranking_loss=best,fixed_ranking_headroom={n:v-best for n,v in fixed.items()},diagnostic_best_order=sorted_order,task_means=means,best_orders=sum(v==best for v in losses.values()),label_scope='Observed task means are information ceilings only, not a proposed price order.')
  report['rules'].append(row);print(row['task'],rule['seed'],'headroom',row['fixed_ranking_headroom']['semantic_v3'],'residual',best,'order',sorted_order,flush=True)
report['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'ranking-ceiling.json',report)
