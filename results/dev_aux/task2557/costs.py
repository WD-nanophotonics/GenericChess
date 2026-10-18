"""Recount every new paid search, including foes/baselines/incomplete queries."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time
O=Path('results/dev_aux/task2557')
def run():
 began=time.perf_counter();rows=[]
 for stage,task in [('matched_candidate_depth',2552),('new_candidate_D3_TRAIN',2555),('new_D3_deployment',2556)]:
  D=Path(f'results/dev_aux/task{task}');p=json.loads((D/'plan.json').read_text());d=json.loads((D/'result.json').read_text());counts=Counter();depth=defaultdict(Counter);games=0
  with(D/'queries.jsonl').open()as f:
   for line in f:
    q=json.loads(line);c=q['color']if stage=='new_candidate_D3_TRAIN'else q['slot'][3];counts['queries']+=1;counts['nodes']+=q['nodes'];counts['search_seconds']+=q['seconds'];counts['candidate_nodes'if q['actor']==c else'foe_nodes']+=q['nodes'];counts['failed_queries']+=not q['complete'];counts['failed_nodes']+=q['nodes']if not q['complete']else 0;depth[q['effective_depth']]['queries']+=1;depth[q['effective_depth']]['nodes']+=q['nodes']
  with(D/'games.jsonl').open()as f:
   for line in f:
    g=json.loads(line);games+=1;counts['actual_terminal']+=g['outcome']is not None;counts['unknown']+=g['outcome']is None
  assert counts['nodes']==d['nodes']
  if stage!='new_candidate_D3_TRAIN':assert counts['queries']==d['queries']and games==d['actual']
  else:assert games==d['counts']['games']and counts['queries']==d['counts']['queries']
  rows.append(dict(stage=stage,task=task,status=d['status'],games=games,planned=d.get('expected',d.get('expected_arms')),missing=d.get('missing'),original_cap=p['cap_seconds'],producer_wall_seconds=d['seconds'],counts=dict(counts),by_depth=[dict(depth=k,**dict(v))for k,v in sorted(depth.items())]))
 total=Counter()
 for r in rows:
  for k,v in r['counts'].items():total[k]+=v
 out=dict(status='PASS_ALL_NEW_PAID_WORK_RECOUNTED',stages=rows,totals=dict(total),listed_producer_wall_seconds=sum(r['producer_wall_seconds']for r in rows),historical93TRAIN_reused_not_executed_again=dict(nodes=6400000,source='4dbba471885be4a6d48a99e7230a007702f27424'),new_unpruned_verification_nodes=sum(json.loads(Path(n).read_text())['nodes']for n in['results/dev_aux/task2553/unpruned.json','results/dev_aux/task2557/unpruned.json']),seconds=time.perf_counter()-began,scope='Every newcandidate/foe/baseline/failed search node charged. Producer elapsed versus search-receipt seconds versus pipeline/audit/encoding/plots/transport/tokens are different; no complete end-to-end equalCPU claim. 2552 originalelapsed includes initialization/repair withzero search; old93training reusedhistorically, not charged asnewexecution. Caps and missing preserved, no load-basedrerun.')
 (O/'costs.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:out[k]for k in['status','totals','listed_producer_wall_seconds','new_unpruned_verification_nodes','seconds']}))
if __name__=='__main__':run()
