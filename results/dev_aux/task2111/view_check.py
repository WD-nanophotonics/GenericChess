"""All-field interface equivalence for a count-triggered materialized view."""
from pathlib import Path
import json,time
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2111')
def run(census="results/dev_aux/task2108",labels="results/dev_aux/task2109",audit="results/dev_aux/task2110"):
 start=time.perf_counter();t=time.perf_counter();view=CanonicalTeacher(census,labels,audit);load=time.perf_counter()-t;n=0
 for raw in Path('results/dev_aux/task2098/labels.jsonl').open(encoding='utf-8'):
  row=json.loads(raw)
  if sum(ch!='.'for ch in row['board'][:-1])>4:continue
  v=view.rows[view.key(row['board'])]
  for k in('board','inventory','status','label','quality','rank','winning_action'):assert row[k]==v[k]
  assert [(e['action'],e['child_value'])for e in row['actions']]==[(e['action'],e['child_value'])for e in v['actions']];n+=1
 assert n==len(view.rows)==244080
 result=dict(status='PASS_ALL_TRIGGER_VISIBLE_FIELDS',states_checked=n,view_load_seconds=load,prior2105_full_load_seconds=json.loads(Path('results/dev_aux/task2105/completion.json').read_text(encoding='utf-8'))['teacher_load_seconds'],view_label_bytes=(Path(labels)/'labels.jsonl').stat().st_size,full_label_bytes=Path('results/dev_aux/task2098/labels.jsonl').stat().st_size,seconds=time.perf_counter()-start,scope='Allprovider-accessedfields equalon<=4captureclosedstates. Above4triggerusesPNanddoesnotreadteacher. Internalchildindicesrenumbered;2110independentallfrontier/coverage/Bellman/rankauditvalidatesclosure. Semanticquerycontract, notwallclockoutputidentity. Loadobservationsdifferenttime/ordinaryconcurrentload, notcleanbenchmark. Derivation9.05s+audit16.42s fromalready593.56spaidteacher; nofrom-scratchCorebuildsavingclaimed. No2105policy/runtimechanged.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
