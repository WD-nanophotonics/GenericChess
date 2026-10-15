"""Paid-trajectory identifiability audit: no engine/prover calls or price choice."""
from pathlib import Path
from collections import defaultdict,Counter
import hashlib,json,time,itertools
OUT=Path('results/dev_aux/task1844')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
 with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def freeze():
 files=[__file__,'results/dev_aux/task1825/games.jsonl','results/dev_aux/task1825/moves.jsonl','results/dev_aux/task1825/selection-before-dev.json']
 write('plan.json',dict(question='Are three paid material prices behaviorally or merely outcome-equivalent, and how often does role averaging hide differences? Describe identifiability, never select/reweight using DEV.',source_sha={str(p):sha(p) for p in files},prices=[360,720,1440],expected_games=384,expected_moves=4748,scope='Exact recorded policy/finite horizon only. UNKNOWN distinct, zero event score is not draw. No interpolation, global optimum, continuity, new game, repeated timing or human reference.'))
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());start=time.perf_counter()
 games=[json.loads(x) for x in Path('results/dev_aux/task1825/games.jsonl').read_text().splitlines()]
 moves=defaultdict(list)
 for line in Path('results/dev_aux/task1825/moves.jsonl').read_text().splitlines():
  row=json.loads(line);moves[row['slot']].append(row)
 assert len(games)==p['expected_games'] and sum(map(len,moves.values()))==p['expected_moves']
 groups=defaultdict(dict)
 for g in games:
  assert len(moves[g['slot']])==g['moves']
  assert all(m['ply']==i for i,m in enumerate(moves[g['slot']]))
  assert [m['choice'] for m in moves[g['slot']]]==g['record']['actions']
  key=(g['phase'],g['family'],g['candidate_side'],g['candidate_proof']);assert g['R'] not in groups[key];groups[key][g['R']]=g
 rows=[];classes=[]
 for key,priced in sorted(groups.items()):
  assert sorted(priced)==p['prices'];phase,family,side,proof=key
  signatures={r:hashlib.sha256(json.dumps((g['record'],g['result'],g['final_state_sha']),sort_keys=True).encode()).hexdigest() for r,g in priced.items()}
  equivalence=defaultdict(list)
  for r,h in signatures.items():equivalence[h].append(r)
  classes.append(dict(phase=phase,family=family,candidate_side=side,proof=proof,trajectory_classes=list(equivalence.values()),outcomes={r:g['outcome'] for r,g in priced.items()},scores={r:g['finite_event_score'] for r,g in priced.items()},all_trajectory_equal=len(equivalence)==1,all_outcome_equal=len({g['outcome'] for g in priced.values()})==1,all_score_equal=len({g['finite_event_score'] for g in priced.values()})==1))
  for low,high in itertools.combinations(p['prices'],2):
   a,b=priced[low],priced[high];aa,bb=moves[a['slot']],moves[b['slot']];first=None
   for i,(ma,mb) in enumerate(zip(aa,bb)):
    if ma['choice']!=mb['choice']:
     assert ma['before_state_sha']==mb['before_state_sha']
     assert ma['side']==mb['side']
     first=dict(ply=i,side=ma['side'],candidate_turn=ma['side']==side,low_source=ma['source'],high_source=mb['source'],before_state_sha=ma['before_state_sha'],low_choice=ma['choice'],high_choice=mb['choice'])
     break
   if first is None:assert signatures[low]==signatures[high]
   rows.append(dict(phase=phase,family=family,candidate_side=side,proof=proof,low=low,high=high,low_slot=a['slot'],high_slot=b['slot'],same_trajectory=signatures[low]==signatures[high],same_outcome=a['outcome']==b['outcome'],same_score=a['finite_event_score']==b['finite_event_score'],score_delta=b['finite_event_score']-a['finite_event_score'],low_outcome=a['outcome'],high_outcome=b['outcome'],first_divergence=first))
 for name,records in [('pairs.jsonl',rows),('classes.jsonl',classes)]:
  with (OUT/name).open('x',encoding='utf-8') as f:
   for x in records:f.write(json.dumps(x)+'\n')
 summaries=[]
 for phase in ('TRAIN','DEV'):
  for proof in (False,True):
   subset=[x for x in classes if x['phase']==phase and x['proof']==proof]
   pairs=[x for x in rows if x['phase']==phase and x['proof']==proof]
   family_scores=defaultdict(lambda:defaultdict(int))
   for x in subset:
    for r,v in x['scores'].items():family_scores[x['family']][r]+=v
   family_flat=sum(len(set(v.values()))==1 for v in family_scores.values())
   summaries.append(dict(phase=phase,proof=proof,role_triplets=len(subset),identical_trajectory_triplets=sum(x['all_trajectory_equal'] for x in subset),identical_outcome_triplets=sum(x['all_outcome_equal'] for x in subset),identical_event_triplets=sum(x['all_score_equal'] for x in subset),families=len(family_scores),event_flat_after_equal_role_average=family_flat,pairs=[dict(low=low,high=high,n=sum(x['low']==low and x['high']==high for x in pairs),trajectory_changed=sum(x['low']==low and x['high']==high and not x['same_trajectory'] for x in pairs),outcome_changed=sum(x['low']==low and x['high']==high and not x['same_outcome'] for x in pairs),event_changed=sum(x['low']==low and x['high']==high and not x['same_score'] for x in pairs),net_delta=sum(x['score_delta'] for x in pairs if x['low']==low and x['high']==high)) for low,high in itertools.combinations(p['prices'],2)]))
 write('result.json',dict(status='COMPLETE',games=len(games),moves=sum(map(len,moves.values())),role_triplets=len(classes),pair_contrasts=len(rows),summaries=summaries,first_divergences=dict(Counter((str(x['first_divergence']['candidate_turn'])+':'+x['first_divergence']['low_source']+':'+x['first_divergence']['high_source']) if x['first_divergence'] else 'IDENTICAL' for x in rows)),seconds=time.perf_counter()-start,new_go_or_proof_or_games=0))
if __name__=='__main__':
 import sys
 {'freeze':freeze,'run':run}[sys.argv[1]]()
