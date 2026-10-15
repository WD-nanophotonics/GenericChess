"""Exact paid proof-query repetition audit; no cache adoption or saved-cost claim."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,time
OUT=Path('results/dev_aux/task1845')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 files=[__file__,'results/dev_aux/task1825/games.jsonl','results/dev_aux/task1825/moves.jsonl','results/dev_aux/task1825/plan.json']
 write('plan.json',dict(question='How often is the SAME full public record/history/target/logical proof budget queried across price counterfactuals, and which observed outcomes can support a future cache contract?',source_sha={str(p):sha(p) for p in files},query_seconds=.0625,proof_depth=64,scope='Offline opportunity bound only, not an implemented cache, measured savings or equivalent time-budget policy. A full-state hash is checked along with exact full public record/target/budget; no position-only merging. Time/cancel failures not reusable as deterministic logical results.'))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());start=time.perf_counter()
 games={g['slot']:g for g in (json.loads(x) for x in Path('results/dev_aux/task1825/games.jsonl').read_text().splitlines())};groups=defaultdict(list);skipped=Counter()
 for line in Path('results/dev_aux/task1825/moves.jsonl').read_text().splitlines():
  m=json.loads(line);g=games[m['slot']];reason=m['proof_reason']
  if reason in ('disabled','verified_strategy','new_proof_disabled'):
   skipped[reason]+=1;continue
  assert m['proof_nodes']>0
  record=dict(g['record']);record['actions']=record['actions'][:m['ply']]
  assert record['resigned_by'] is None and record.get('declaration') is None
  key=json.dumps(dict(state_sha=m['before_state_sha'],record=record,target=m['side'],proof_nodes_cap=m['budget']//4,seconds=p['query_seconds'],max_depth=p['proof_depth']),sort_keys=True,separators=(',',':'))
  groups[key].append(dict(slot=m['slot'],ply=m['ply'],R=g['R'],family=g['family'],phase=g['phase'],candidate_side=g['candidate_side'],candidate_proof=g['candidate_proof'],side=m['side'],budget=m['budget']//4,nodes=m['proof_nodes'],reason=reason,source=m['source'],rank=m['after_ranks'][m['side']],total_decision_seconds=m['seconds']))
 rows=[]
 for key,observations in groups.items():
  logical=[x for x in observations if x['reason'] in ('node_budget','no_forced_win_in_exhausted_tree','finite_session_all_defense_certificate','verification_time_budget')]
  signatures=Counter((x['reason'] if x['reason']!='verification_time_budget' else 'finite_session_all_defense_certificate',x['nodes']) for x in logical)
  rows.append(dict(query_sha=hashlib.sha256(key.encode()).hexdigest(),multiplicity=len(observations),logical_completed=len(logical),distinct_logical_signatures=[dict(reason=k[0],nodes=k[1],count=v) for k,v in signatures.items()],mixed_logical_signatures=len(signatures)>1,observations=observations))
 rows.sort(key=lambda x:(-x['multiplicity'],x['query_sha']))
 with (OUT/'queries.jsonl').open('x',encoding='utf-8') as f:
  for row in rows:f.write(json.dumps(row)+'\n')
 allobs=[x for r in rows for x in r['observations']];completed=[r for r in rows if r['logical_completed']]
 repeat_time=sum(max(0,sum(x['reason']=='time_budget' for x in r['observations'])-1) for r in rows)
 write('result.json',dict(status='COMPLETE',proof_calls=len(allobs),unique_full_queries=len(rows),duplicate_calls=sum(r['multiplicity']-1 for r in rows),skipped=dict(skipped),reason_counts=dict(Counter(x['reason'] for x in allobs)),logical_completed_calls=sum(r['logical_completed'] for r in rows),unique_queries_with_logical_completion=len(completed),repeat_logical_completions=sum(max(0,r['logical_completed']-1) for r in rows),logical_signature_mismatches=sum(r['mixed_logical_signatures'] for r in rows),repeat_time_exhaustions=repeat_time,repeat_time_exhaustion_at_least_phase_seconds=repeat_time*p['query_seconds'],all_proof_nodes=sum(x['nodes'] for x in allobs),repeat_logical_nodes=sum(sum(x['nodes'] for x in r['observations'] if x['reason']!='time_budget')-next(x['nodes'] for x in r['observations'] if x['reason']!='time_budget') for r in completed),seconds=time.perf_counter()-start,warning='No cache implementation, rerun or elapsed saving measured. Identical logical signatures do not bind exact certificate trees not saved in these logs. Reusing UNKNOWN under fixed wall changes opportunity; per-phase budgets and real/charged costs must be separated first. No old game scores or fixed opponent changed.'))
if __name__=='__main__':
 import sys
 {'freeze':freeze,'run':run}[sys.argv[1]]()
