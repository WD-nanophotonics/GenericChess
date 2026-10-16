"""Freeze every actual candidate LOW attempt before any new labels/queries."""
from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2311')
def run():
 source=Path('results/dev_aux/task2307/decisions.jsonl');plans=json.loads(Path('results/dev_aux/task2307/plan.json').read_text());slots={r['slot']:r for r in json.loads(Path('results/dev_aux/task2307/slots.json').read_text())};roots={r['index']:r for r in json.loads(Path(plans['input']).read_text())};rows=[];contexts=[];index={}
 for d in map(json.loads,source.read_text().splitlines()):
  if not d['is_candidate']or not d['new_proof_attempt']:continue
  assert d['regime']=='LOW'and d['caller_seconds']==8.
  slot=slots[d['slot']];r=roots[slot['root']];key=json.dumps(dict(rules=r['rules'],record=d['root_record']),sort_keys=True);key=hashlib.sha256(key.encode()).hexdigest()
  if key not in index:
   index[key]=len(contexts);contexts.append(dict(context=len(contexts),key=key,rules=r['rules'],root_record=d['root_record'],root_state_sha=d['root_state_sha'],side=d['side'],occurrences=[]))
  row=dict(context=index[key],slot=d['slot'],root=slot['root'],ratio=slot['ratio'],candidate_color=slot['candidate_color'],ply=d['ply'],remaining_horizon=plans['H']-d['ply']);rows.append(row);contexts[index[key]]['occurrences'].append(row)
 assert len(rows)==27
 result=dict(selection='ALLactualcandidateLOWnewproofattempts fromALL32closed2307slots; no newlabel/outcome/proofsuccess filtering. Dedupfullrulepath+actualrootrecord, preservealloccurrences/remainingH.',source=str(source).replace('\\','/'),source_sha=hashlib.sha256(source.read_bytes()).hexdigest(),source_plan_sha=hashlib.sha256(Path('results/dev_aux/task2307/plan.json').read_bytes()).hexdigest(),occurrences=rows,contexts=contexts,labels_read=False,new_queries=0,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with(OUT/'inputs.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(occurrences=len(rows),contexts=len(contexts),remaining=[min(r['remaining_horizon']for r in c['occurrences'])for c in contexts])))
if __name__=='__main__':run()
