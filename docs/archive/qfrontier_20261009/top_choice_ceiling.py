"""Descriptive best-fixed and context/slot ceilings, not trained prices.
Reuse complete original populations and equal-slot then equal-background law.
Always choosing each type is scored on ALL rows, including no-reply/zero rows.
Observed labels define ceilings only; no predictor deployment or holdout claim.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import json,hashlib,sys
sys.path.insert(0,str(Path.cwd()))
from scripts.research_record import write_record
p=Path(__file__).parent;result=dict(scope=__doc__,inputs={},rules=[])
for taskfile,declfile,analysisfile in [('reply-task.json','reply-declaration.json','reply-analysis.json'),('reply8-task.json','reply8-declaration.json','reply8-analysis.json')]:
 data=json.loads((p/taskfile).read_bytes());decl=json.loads((p/declfile).read_bytes());prior=json.loads((p/analysisfile).read_bytes())
 for name in (taskfile,declfile,analysisfile):result['inputs'][name]=hashlib.sha256((p/name).read_bytes()).hexdigest()
 for r in data['rules']:
  assert r['complete'];types=r['types'];tables=decl['prices'][str(r['seed'])];bg=defaultdict(dict)
  for c in r['cells']:bg[c['ply']].setdefault(c['source'],{})[c['type']]=c
  assert len(bg)==17 and all(sorted(v)==types for slots in bg.values() for v in slots.values())
  row=dict(seed=r['seed'],tasks={})
  for field in ('immediate','task'):
   means={t:sum((sum((F(v[t][field]) for v in slots.values()),F())/len(slots) for slots in bg.values()),F())/17 for t in types}
   oracle=sum((sum((F(max(v[t][field] for t in types)) for v in slots.values()),F())/len(slots) for slots in bg.values()),F())/17
   context_value=sum((max(sum((F(v[t][field]) for v in slots.values()),F())/len(slots) for t in types) for slots in bg.values()),F())/17
   constant_losses={t:oracle-means[t] for t in types};best=min(constant_losses.values());context_loss=oracle-context_value
   fixed={name:oracle-sum((means[t] for t in types if table[t]==max(table[t] for t in types)),F())/sum(table[t]==max(table[t] for t in types) for t in types) for name,table in tables.items()}
   observed=next(x for x in prior['rules'] if x['seed']==r['seed'])['summary'][field]['losses']
   assert all(F(observed[n])==v for n,v in fixed.items())
   assert 0<=context_loss<=best<=min(fixed.values())
   row['tasks'][field]=dict(oracle_mean=oracle,constant_losses=constant_losses,best_fixed_types=[t for t in types if constant_losses[t]==best],fixed_losses=fixed,best_fixed_loss=best,context_oracle_loss=context_loss,fixed_choice_headroom={n:v-best for n,v in fixed.items()},unavoidable_fixed_loss=best,context_only_reduction=best-context_loss,remaining_slot_loss=context_loss,blind_loss=oracle-sum(means.values(),F())/len(types))
  result['rules'].append(row)
  print(r['seed'],{k:dict(best=v['best_fixed_types'],headroom=str(v['fixed_choice_headroom']['semantic_v3']),unavoidable=str(v['unavoidable_fixed_loss']),oracle=str(v['oracle_mean'])) for k,v in row['tasks'].items()},flush=True)
result['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(p/'top-choice-ceiling.json',result)
