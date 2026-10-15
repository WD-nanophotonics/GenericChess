"""Paid price-opportunity audit: actual Normal decisions, proof-only constants."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time
OUT=Path('results/dev_aux/task1901')
def run():
 start=time.perf_counter();reports=[]
 for task in (1881,1890):
  folder=Path('results/dev_aux/task'+str(task));games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()];moves=defaultdict(list)
  for line in (folder/'moves.jsonl').read_text().splitlines():
   m=json.loads(line);moves[m['slot']].append(m)
  groups=defaultdict(list)
  for g in games:groups[g['phase'],g.get('opponent_nodes',64),g['family'],g['candidate_side']].append(g)
  counts=defaultdict(Counter);details=[]
  for (phase,opponent,family,role),gs in groups.items():
   c=counts[phase+':opponent'+str(opponent)];c['family_role_groups']+=1
   active=[sum(m['side']==role and m['source']=='EXTERNAL_SEARCH' for m in moves[g['slot']]) for g in gs]
   paths=[json.dumps([m['choice'] for m in moves[g['slot']]],sort_keys=True) for g in gs];scores=[g['finite_event_score'] for g in gs];outcomes=[g['outcome'] for g in gs]
   c['some_candidate_normal']+=any(active);c['all_candidate_normal']+=all(active);c['all_zero_candidate_normal']+=not any(active);c['different_action_path']+=len(set(paths))>1;c['different_event_score']+=len(set(scores))>1
   c['different_path_but_flat_event']+=len(set(paths))>1 and len(set(scores))==1
   if not any(active):assert len(set(scores))==1;details.append(dict(phase=phase,opponent=opponent,family=family,role=role,slots=[g['slot'] for g in gs],outcomes=outcomes,normal_calls=active))
  reports.append(dict(task=task,groups={k:dict(v) for k,v in counts.items()},theta_inactive_groups=details))
 out=dict(status='COMPLETE_PAID_ACTUAL_PRICE_OPPORTUNITY',reports=reports,seconds=time.perf_counter()-start,new_go=0,new_proof_calls=0,new_games=0,scope='Normal-call absence certifies this actualtrace never consulted theta; differingpaths withflatevents show sparsefinitefeedback, not proof of permanentirrelevance. No posthocrootremoval/selection, source/rewardchanges or theoryWIN label. A future inputcondition must be frozen separately and price/outcome-independent.')
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({**out,'reports':[{k:v for k,v in r.items() if k!='theta_inactive_groups'} for r in reports]}))
if __name__=='__main__':run()
