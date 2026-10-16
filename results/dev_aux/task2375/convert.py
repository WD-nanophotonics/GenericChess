"""Actual proof-entry/conversion accounting for the frozen selected price contrast."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time,hashlib
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2375')
def run(task=2358):
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();f=Path(f'results/dev_aux/task{task}');p=json.loads((f/'plan.json').read_text());selected=float(json.loads(Path('results/dev_aux/task2357/selection.json').read_text())['selected_price']);prices=[1.,selected];games=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];ds=defaultdict(list)
 for d in map(json.loads,(f/'decisions.jsonl').read_text().splitlines()):ds[d['slot']].append(d)
 summaries={};proof_slots={};all_entries=[]
 for price in prices:
  gg=[g for g in games if g['ratio']==price];entries=[];calls=0
  for g in gg:
   stop();ordinary=0;proof=False
   for d in ds[g['slot']][:g['plies']]:
    if not d['is_candidate']:continue
    calls+=bool(d['new_proof_attempt'])
    if d['source']=='FULL_SESSION_MATERIAL_SEARCH':ordinary+=1
    if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY'):
     proof=True;entry=dict(slot=g['slot'],family=g['root'],opponent=g['opponent'],color=g['candidate_color'],price=price,ply=d['ply'],ordinary_material_commits_before=ordinary,root_record=d['root_record'],root_state_sha=d['root_state_sha'],context_sha=hashlib.sha256(json.dumps([d['root_state_sha'],d['root_record']],sort_keys=True).encode()).hexdigest(),actual_outcome=g['outcome'],converted_actual_win=g['outcome']=='W');entries.append(entry)
   proof_slots[g['slot']]=proof
  summaries[str(price)]=dict(actual_returned=len(gg),outcomes=dict(Counter(g['outcome']for g in gg)),terminal_statuses=dict(Counter(g['actual_status']for g in gg)),new_proof_attempts=calls,admissions=len(entries),unique_fullhistory_admissions=len({r['context_sha']for r in entries}),admitted_and_actual_won=sum(r['converted_actual_win']for r in entries),actual_wins_without_own_proof=sum(g['outcome']=='W'and not proof_slots[g['slot']]for g in gg),all_admissions_after_ordinary=all(r['ordinary_material_commits_before']>0 for r in entries));all_entries+=entries
 by=defaultdict(dict)
 for g in games:
  if g['ratio']in prices:by[(g['root'],g['opponent'],g['candidate_color'])][g['ratio']]=g
 changed=[]
 for key,pair in sorted(by.items()):
  if set(pair)!=set(prices)or any(g['reward']is None for g in pair.values()):continue
  a,b=[pair[price]for price in prices];delta=b['reward']-a['reward']
  if delta:changed.append(dict(family=key[0],opponent=key[1],color=key[2],actual_outcomes=[a['outcome'],b['outcome']],delta=delta,own_proof_admitted=[proof_slots[a['slot']],proof_slots[b['slot']]]))
 result=dict(status='PASS_ACTUAL_SELECTED_PAIR_PROOF_CONVERSION_ACCOUNTING',task=task,prices=summaries,changed_actual_reward_pairs=changed,entries=all_entries,seconds=time.perf_counter()-t,scope='Closed/returnedgame records only, originaladmissions andactualW-L separate. Unreturnedpartialjournal handledby ownjournalconsumer; unknownnotactualwin/draw. Morecalls/admissions alone notutility orlargerunderlyingWINset; unprovedentriesunknown. Proof aftermaterial choices + convertedwin isassociation, notcausalmediation; no offpolicyproof/extraquery/reward substitution. Samefixedstrategy/resources/foe withinpairs, TRAINandreservedpanelsnotpooled.')
 with(OUT/f'task{task}-result.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='entries'}))
if __name__=='__main__':import sys;run(int(sys.argv[1])if len(sys.argv)>1 else 2358)
