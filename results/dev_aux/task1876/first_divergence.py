"""Counterfactual first-divergence attribution on already paid768games."""
from pathlib import Path
from collections import defaultdict,Counter
from itertools import combinations
import json,time
OUT=Path('results/dev_aux/task1876')
def run():
 beg=time.perf_counter();games=[json.loads(x) for x in Path('results/dev_aux/task1869/games.jsonl').read_text().splitlines()];moves=defaultdict(list)
 for line in Path('results/dev_aux/task1869/moves.jsonl').read_text().splitlines():
  row=json.loads(line);moves[row['slot']].append(row)
 by=defaultdict(dict)
 for game in games:by[game['family'],game['candidate_side']][game['N'],game['ratio']]=game
 details=[];summaries={}
 for axis in ('RATIO_WITHIN_UNIT','UNIT_WITHIN_RATIO'):
  count=Counter();categories=Counter();reasons=Counter()
  for (family,role),index in sorted(by.items()):
   for (ka,a),(kb,b) in combinations(sorted(index.items()),2):
    if axis=='RATIO_WITHIN_UNIT' and not(ka[0]==kb[0] and ka[1]!=kb[1]):continue
    if axis=='UNIT_WITHIN_RATIO' and not(ka[1]==kb[1] and ka[0]!=kb[0]):continue
    count['pairs']+=1;left,right=moves[a['slot']],moves[b['slot']];count['same_actual_outcomes']+=a['outcome']==b['outcome'];count['same_event_score']+=a['finite_event_score']==b['finite_event_score']
    diverged=next((i for i,(x,y) in enumerate(zip(left,right)) if x['choice']!=y['choice']),None)
    if diverged is None:
     count['same_action_paths']+=len(left)==len(right)
     if len(left)!=len(right):count['prefix_only_same']+=1;details.append(dict(axis=axis,family=family,role=role,slots=[a['slot'],b['slot']],prefix_only=True))
     continue
    x,y=left[diverged],right[diverged];assert x['before_state_sha']==y['before_state_sha'] and x['side']==y['side'];owner='CANDIDATE' if x['side']==role else 'FIXED_OPPONENT';category=owner+':'+x['source']+'|'+y['source'];categories[category]+=1;count['first_divergences']+=1
    if owner=='CANDIDATE' and x['source']==y['source']=='EXTERNAL_SEARCH':count['candidate_normal_first_divergences']+=1
    else:
     reasons[x['proof_reason']+'|'+y['proof_reason']]+=1;details.append(dict(axis=axis,family=family,role=role,slots=[a['slot'],b['slot']],first_ply=diverged,category=category,receipts=[{k:m.get(k) for k in ('source','proof_reason','exit_cause','proof_nodes','verification_nodes','search_nodes','seconds','bank_hit','bank_stored','logical_status','logical_reason','fill_verification_nodes','fill_verification_seconds','verification_seconds','before_ranks','proof_stats')} for m in (x,y)],outcomes=[a['outcome'],b['outcome']]))
  summaries[axis]=dict(counts=dict(count),first_divergence_categories=dict(categories),non_normal_reason_pairs=dict(reasons))
 result=dict(status='COMPLETE_PAID_COUNTERFACTUAL_AUDIT',summaries=summaries,non_normal_or_prefix_details=details,seconds=time.perf_counter()-beg,new_games=0,new_go=0,new_proofs=0,scope='Each axis fixesfamily/role/opponent/otherpricecoordinate; pair counts share roots and areNOT independent samples. First normalcandidate divergence is consistent with changedmaterialpolicy, not proof of betterWDL. Non-normal/fixedopponent/prefix-only divergence needs explicit resource/cursor inspection, not automatically called price effect. Original outcomes, budgets and timefailures preserved.')
 with (OUT/'report.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='non_normal_or_prefix_details'}))
if __name__=='__main__':run()
