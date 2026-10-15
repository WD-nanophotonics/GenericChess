"""Recompute the preserved offline newphase repetition opportunity exactly."""
from pathlib import Path
from collections import defaultdict
import json

def compute():
 games={g['slot']:g for g in (json.loads(x) for x in Path('results/dev_aux/task1848/games.jsonl').read_text().splitlines())};groups=defaultdict(list)
 for line in Path('results/dev_aux/task1848/moves.jsonl').read_text().splitlines():
  m=json.loads(line)
  if m['proof_reason'] in ('disabled','verified_strategy','new_proof_disabled'):continue
  record=dict(games[m['slot']]['record']);record['actions']=record['actions'][:m['ply']];caps=m['phase_limits']
  key=json.dumps(dict(fp=record['ruleset_fingerprint'],state_sha=m['before_state_sha'],record=record,target=m['side'],proof_nodes=caps['proof_nodes'],proof_seconds=caps['proof_seconds'],proof_depth=64,verification_nodes=caps['verification_nodes'],verification_seconds=caps['verification_seconds']),sort_keys=True,separators=(',',':'))
  groups[key].append(m)
 avoided=0.;nodes=calls=eligible=0
 for rows in groups.values():
  first=next((i for i,m in enumerate(rows) if m['proof_reason'] in ('node_budget','no_forced_win_in_exhausted_tree') or m['source']=='PROOF'),None)
  if first is not None:
   eligible+=1;calls+=len(rows[first+1:]);avoided+=sum(m['proof_seconds'] for m in rows[first+1:]);nodes+=sum(m['proof_nodes'] for m in rows[first+1:])
 return dict(calls=sum(map(len,groups.values())),unique_complete_keys=len(groups),eligible_keys=eligible,possible_post_first_completion_calls=calls,possible_avoided_paid_proof_seconds=avoided,possible_avoided_proof_nodes=nodes)
if __name__=='__main__':
 actual=compute();saved=json.loads(Path('results/dev_aux/task1855/result.json').read_text())
 for k,v in actual.items():assert abs(saved[k]-v)<1e-8,(k,saved[k],v)
 print(json.dumps(dict(status='EXACT_PAID_DATA_RECOMPUTATION_PASS',**actual)))
