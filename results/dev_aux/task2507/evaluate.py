"""Common PLAIN deployment: initial baseline paid once, BOTHtrained regimes kept."""
from pathlib import Path
import json,random,time,hashlib,datetime
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2507')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();done=json.loads(Path(p['training']).read_text());assert done['status']=='COMPLETE'and len(done['arms'])==p['expected_arms'];assert hashlib.sha256(Path(p['training']).read_bytes()).hexdigest()==p['training_sha'];arms={(a['seed'],a['quiet']):a for a in done['arms']};stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())));rows=[];status='COMPLETE'
 with(OUT/'games.jsonl').open('x')as f:
  for seed in p['seeds']:
   for family in p['families']:
    for color in (0,1):
     for treatment in ('initial','plain_trained','q2_trained'):
      initial=arms[(seed,False)]['initial'];assert initial==arms[(seed,True)]['initial'];w=initial if treatment=='initial'else arms[(seed,treatment=='q2_trained')]['weights'];candidate=Model(w);foe=Model(p['foe_weights']);env=ChessEnv();rng=random.Random(family)
      for _ in range(p['opening_plies']):
       if env.terminal()is not None:break
       env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
      prefix=env.record();nodes=0;outcome=None;reason='HORIZON_UNKNOWN'
      for ply in range(p['H']):
       stop();outcome=env.terminal()
       if outcome is not None:reason='ACTUAL_TERMINAL';break
       left=p['cap_seconds']-(time.perf_counter()-start)
       if left<=0:reason='GLOBAL_CAP_UNKNOWN';status='PARTIAL_CAP';break
       r=TrainingSearch(p['depth'],quiet=False).search(env,candidate if env.player()==color else foe,nodes=p['nodes_per_query'],seconds=min(p['seconds_per_query'],left),seed=family*10000+ply+p['ordering_seed_offset'],cancel=stop);nodes+=r.nodes
       if not r.complete:reason='SEARCH_LIMIT_UNKNOWN';break
       if r.action is None:raise AssertionError('ongoing complete root without action')
       env.push(r.action)
      actual=env.terminal()
      if actual is not None:outcome=actual;reason='ACTUAL_TERMINAL'
      reward=None if outcome is None else outcome*(1 if color==0 else-1);row=dict(seed=seed,family=family,color=color,treatment=treatment,weights=w,initial_record=prefix,record=env.record(),reward=reward,ending=reason,nodes=nodes);rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
      if status!='COMPLETE':break
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   print(json.dumps(dict(seed=seed,games_completed=len(rows),seconds=time.perf_counter()-start)),flush=True)
   if status!='COMPLETE':break
 summaries=[]
 for seed in p['seeds']:
  tally={}
  for treatment in ('initial','plain_trained','q2_trained'):
   rr=[r for r in rows if r['seed']==seed and r['treatment']==treatment];tally[treatment]={k:sum(r['reward']==v for r in rr)for k,v in [('W',1),('L',-1),('D',0),('U',None)]}
  summaries.append(dict(seed=seed,tallies=tally))
 result=dict(status=status,expected=p['expected_games'],actual=len(rows),nodes=sum(r['nodes']for r in rows),seconds=time.perf_counter()-start,results=summaries,scope='NEW16family/4initials/BOTHtraining regimes, commonPLAIN D2/pathseeded deployment and uniformfoe; oneinitialbaselineperseed/family/role paidONCE and explicitlyshared. Measures training-regime usefulness underthisdeployment, NOT q-enabled play or puretarget mediation. AllU/missing kept, no fit/selection.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
