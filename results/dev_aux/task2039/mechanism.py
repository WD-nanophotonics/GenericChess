"""Frozen unit study trajectory forks and executable proof-entry outcomes."""
from pathlib import Path
from collections import Counter,defaultdict
import json,statistics
P=Path('results/dev_aux/task2030');O=Path('results/dev_aux/task2039')
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def main():
 games=lines(P/'games.jsonl');moves=lines(P/'moves.jsonl');by=defaultdict(list)
 for x in moves:by[x['slot']].append(x)
 cells={(g['family'],g['candidate_side'],g['profile_index']):g for g in games};pairs=[];proofs=[]
 for g in games:
  trajectory=by[g['slot']];entry=next((x for x in trajectory if x['source']=='PROOF'),None)
  if entry is not None:
   assert g['result']['winner']==entry['side'] and g['outcome'] in ('WIN','LOSS')
   proofs.append(dict(slot=g['slot'],family=g['family'],profile=g['profile_index'],outcome=g['outcome'],candidate_proved=entry['side']==g['candidate_side'],entry_ply=entry['ply'],entry_state_sha=entry['before_state_sha'],end_ply=g['moves'],realization_plies=g['moves']-entry['ply'],rank_after=entry['after_ranks'][entry['side']]))
 for a,b,label in ((0,1,'RATIO_N360'),(2,3,'RATIO_N720'),(0,2,'UNIT_RATIO1'),(1,3,'UNIT_RATIO4')):
  for f in range(8):
   for side in range(2):
    ga,gb=cells[f,side,a],cells[f,side,b];ta,tb=by[ga['slot']],by[gb['slot']];prefix=0
    for xa,xb in zip(ta,tb):
     if xa['choice']!=xb['choice']:break
     assert xa['before_state_sha']==xb['before_state_sha'];prefix+=1
    fork=prefix<min(len(ta),len(tb))
    if fork:assert ta[prefix]['before_state_sha']==tb[prefix]['before_state_sha']
    pairs.append(dict(contrast=label,family=f,candidate_side=side,slots=[ga['slot'],gb['slot']],outcomes=[ga['outcome'],gb['outcome']],score_delta=gb['finite_event_score']-ga['finite_event_score'],common_prefix=prefix,action_fork=fork,fork_actor=('CANDIDATE' if ta[prefix]['side']==side else 'OPPONENT') if fork else None,fork_sources=[ta[prefix]['source'],tb[prefix]['source']] if fork else None))
 summary={}
 for label in sorted({x['contrast'] for x in pairs}):
  xs=[x for x in pairs if x['contrast']==label]
  summary[label]=dict(pairs=len(xs),forks=sum(x['action_fork'] for x in xs),fork_families=sorted({x['family'] for x in xs if x['action_fork']}),outcome_changes=sum(x['outcomes'][0]!=x['outcomes'][1] for x in xs),fork_actors=dict(Counter(x['fork_actor'] for x in xs if x['action_fork'])),transitions=dict(Counter('->'.join(x['outcomes']) for x in xs)))
 result=dict(status='PASS_EXISTING_TRAJECTORY_DIAGNOSTIC',summary=summary,pairs=pairs,proofs=proofs,proof_entry_count=len(proofs),all_proof_entries_realized=True,scope='Existing frozen study, no new search. First same-state fork is a trajectory mechanism, not isolated downstream counterfactual causation. Proof entry count alone is not advantage; actual candidate W/L and realization retained. No equal-unit equivalence or human-price inference.')
 (O/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(summary=summary,proofs=len(proofs))))
if __name__=='__main__':main()
