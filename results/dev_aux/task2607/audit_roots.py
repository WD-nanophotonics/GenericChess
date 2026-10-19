"""Outcome-blind deterministic root feasibility audit for task2607."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
from results.dev_aux.task2606.train import compiled,environment,prefix
D=Path('results/dev_aux/task2607')
plan=json.loads((D/'plan.json').read_text(encoding='utf-8')); reg=json.loads((D/'registration.json').read_text(encoding='utf-8'))
assert reg['state']=='REGISTERED_BEFORE_AUDIT'
assert hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()==reg['plan_sha256']
for name,h in reg['source_pins'].items(): assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
train_lo,train_hi=plan['training_family_ids']; eval_lo,eval_hi=plan['evaluation_candidate_family_ids']; required=plan['minimum_selected_unique_disjoint_roots_per_rule']
results={}; all_rows=[]; sufficient=True
for gs in plan['rules']:
 cc=compiled(gs); train_ids=set(); train_dups=0
 for family in range(train_lo,train_hi+1):
  e=environment(gs,cc);prefix(e,gs,family,plan['prefix_plies']); rec=e.record()
  if e.terminal() is not None or len(rec['actions'])<plan['prefix_plies']: continue
  ident=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=False)
  if ident in train_ids: train_dups+=1
  train_ids.add(ident)
 selected=set(); selected_fams=[]; counts=Counter(); rows=[]
 for family in range(eval_lo,eval_hi+1):
  e=environment(gs,cc);prefix(e,gs,family,plan['prefix_plies']);rec=e.record()
  ident=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=False)
  if e.terminal() is not None or len(rec['actions'])<plan['prefix_plies']: reason='PREFIX_TERMINAL_OR_SHORT'
  elif ident in train_ids: reason='TRAIN_EXACT_RECORD_OVERLAP'
  elif ident in selected: reason='EVAL_EXACT_RECORD_DUPLICATE'
  elif len(selected_fams)<required: reason='ACCEPT_FIRST_16';selected.add(ident);selected_fams.append(family)
  else: reason='VALID_AFTER_TARGET';selected.add(ident)
  counts[reason]+=1; rows.append({'family':family,'reason':reason,'record':rec})
 all_rows.extend({'rule':gs,**r} for r in rows)
 ok=len(selected_fams)>=required;sufficient &= ok
 results[str(gs)]={'training_family_roots':train_hi-train_lo+1,'unique_valid_training_records':len(train_ids),'duplicate_training_records':train_dups,'eval_candidate_roots':eval_hi-eval_lo+1,'classification_counts':dict(counts),'selected_family_ids':selected_fams,'selected_count':len(selected_fams),'status':'PASS' if ok else 'INSUFFICIENT_ROOTS'}
out={'task':plan['task'],'status':'PASS' if sufficient else 'INSUFFICIENT_ROOTS','plan_sha256':reg['plan_sha256'],'rules':results,'root_rows_sha256':None,'scope':'Feasibility of exact record-disjoint 4-ply starts only; not a trained result, outcome estimate, or all-history-state holdout.'}
raw=json.dumps(all_rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();out['root_rows_sha256']=hashlib.sha256(raw).hexdigest();(D/'root-candidates.json').write_bytes(raw);(D/'result.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(out,indent=2))