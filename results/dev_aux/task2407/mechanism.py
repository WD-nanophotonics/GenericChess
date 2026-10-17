"""Post-fit actual first-divergence evidence, not causal mediation."""
from pathlib import Path
from collections import Counter
import json,time
OUT=Path('results/dev_aux/task2407')
def run():
 tick=time.perf_counter();selection=json.loads(Path('results/dev_aux/task2405/selection.json').read_text());chosen=selection['selected'];base=[1.5,1.5];panels=[]
 for task in(2401,2402):
  f=Path(f'results/dev_aux/task{task}');games=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));ds=list(map(json.loads,(f/'decisions.jsonl').read_text().splitlines()));by={g['slot']:[d for d in ds if d['slot']==g['slot']]for g in games};pairs=[];normal=Counter();sources=Counter(d['source']for d in ds)
  for d in ds:
   if d['normal_receipt']is not None:normal[(d['is_candidate'],d['normal_receipt']['completed_depth'])]+=1
  if chosen!=base:
   for family in range(8):
    for role in(0,1):
     matches=[next((g for g in games if g['root']==family and g['candidate_color']==role and[g['ratio'],g['hand_ratio']]==p),None)for p in(base,chosen)];a,b=matches
     if a is None or b is None:pairs.append(dict(family=family,role=role,missing=True));continue
     first=None
     for x,y in zip(by[a['slot']],by[b['slot']]):
      if x['choice']!=y['choice']:
       assert x['root_record']==y['root_record']and x['root_state_sha']==y['root_state_sha'];first=dict(ply=x['ply'],side=x['side'],is_candidate=x['is_candidate'],sources=[x['source'],y['source']],normal_depths=[None if z['normal_receipt']is None else z['normal_receipt']['completed_depth']for z in(x,y)]);break
     pairs.append(dict(family=family,role=role,first_divergence=first,identical_records=a['record']==b['record'],outcomes=[a['outcome'],b['outcome']],reward_gain=None if a['reward']is None or b['reward']is None else b['reward']-a['reward']))
  panels.append(dict(task=task,pairs=pairs,normal_depths=[dict(candidate=k[0],depth=k[1],count=v)for k,v in normal.items()],sources=dict(sources),actual_game_seconds=sum(g['seconds']for g in games),candidate_decision_seconds=sum(d['measured_seconds']for d in ds if d['is_candidate']),foe_decision_seconds=sum(d['measured_seconds']for d in ds if not d['is_candidate'])))
 (OUT/'result.json').write_text(json.dumps(dict(status='PASS_ACTUAL_FIRST_DIVERGENCES_AND_COST',panels=panels,seconds=time.perf_counter()-tick,scope='Same-root firstchoice differences only. Source/depth/timing distinguish prices from caller truncation, not proof of mediation/all-policyequivalence. Baseline chosen yields no alternativepair; no fake zero-gain replication. No newgames/search/refitting.'),indent=2));print(json.dumps(panels))
if __name__=='__main__':run()
