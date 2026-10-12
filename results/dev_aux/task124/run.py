"""Frozen matched opening-distribution comparison; no adaptive stage growth."""
import copy,hashlib,importlib.util,json,math,random,sys,time
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task124'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
C=module('reuse123_for124','results/dev_aux/task123/run.py');adapter=C.adapter;G=C.G
E=module('schedule108_for124','results/dev_aux/task108/evolution.py')
SEEDS=(103,104,105);GENERATIONS=6;OPENINGS=8
# All starts/deltas fixed before execution; reference appears only in later analysis.

def execute():
 stop=lambda:adapter.stop_check(ROOT);stop()
 binary,digest,q=adapter.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json')
 if (OUT/'events.jsonl').exists():raise FileExistsError('No rerun or result-driven extension')
 started=time.monotonic();deadline=started+600;journal=adapter.Journal(OUT/'events.jsonl');calls=[];runs=[];active=None
 def block(weights,contexts,opening_plies):
  nonlocal active
  if active is not None:raise RuntimeError('one owned process only')
  adapter.guard(deadline,stop);active=adapter.UCI(binary,ROOT,deadline,stop);active.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
  values=[]
  try:
   for x in contexts:
    adapter.guard(deadline,stop)
    result=adapter.play_game(active,weights,x,deadline,OUT/'variant.ini',journal,lambda seed:G.opening(seed,plies=opening_plies),G.score,stop,cap=16)
    adapter.guard(deadline,stop)
    calls.append(dict(context=x,weights=dict(weights),result=result));values.append(result['reward'])
    if len(calls)%48==0:
     adapter.atomic_json(OUT/'progress.json',dict(completed_games=len(calls),wall_seconds=time.monotonic()-started,current=x['name']))
     print(json.dumps(dict(completed_games=len(calls),wall_seconds=round(time.monotonic()-started,3))),flush=True)
  finally:active.close();active=None
  return values
 def contexts(seed,opening_plies,generation,arm,phase):
  result=[]
  for oi in range(OPENINGS):
   for color in (True,False):
    os=83000+generation*OPENINGS+oi if phase=='train' else 85000+oi
    rs=93000+generation*OPENINGS+oi if phase=='train' else 95000+oi
    result.append(dict(opening_seed=os,random_seed=rs,agent_color=color,phase=phase,name=f's{seed}-p{opening_plies}-{phase}-g{generation}-a{arm}-o{oi}-c{int(color)}'))
  return result
 try:
  for seed in SEEDS:
   # Opposite distribution order for alternating seeds; both arms same schedule.
   for op in ((6,24) if seed%2 else (24,6)):
    theta=E.starts(seed);rng=random.Random(seed+900000);run=dict(seed=seed,opening_plies=op,initial_weights=E.weights(theta),iterations=[],heldout=[]);runs.append(run)
    for generation in range(GENERATIONS):
     delta=[rng.choice((-1,1)) for _ in E.TYPES]
     candidates=[theta[:]]+[[max(E.LOW,min(E.HIGH,t+sgn*.4*z)) for t,z in zip(theta,delta)] for sgn in (1,-1)]
     groups=[block(E.weights(t),contexts(seed,op,generation,a,'train'),op) for a,t in enumerate(candidates)]
     means=[sum(r)/len(r) for r in groups];chosen=E.select(means);before=E.weights(theta);theta=candidates[chosen][:]
     run['iterations'].append(dict(generation=generation,before=before,delta=delta,means=means,rewards=groups,selected=chosen,after=E.weights(theta)))
    run['final_weights']=E.weights(theta)
    for arm in ('initial','final'):
     cs=contexts(seed,op,0,arm,'heldout');rewards=block(run[arm+'_weights'],cs,op)
     run['heldout'] += [dict(arm=arm,opening_index=idx//2,color=x['agent_color'],reward=reward) for idx,(x,reward) in enumerate(zip(cs,rewards))]
    adapter.atomic_json(OUT/'partial.json',dict(completed=False,runs=runs,calls=calls))
  state='COMPLETE'
 except BaseException as err:
  state='INTERRUPTED';error=type(err).__name__+': '+str(err)
 finally:
  if active:active.close()
  journal.close()
 result=dict(completed=state=='COMPLETE',scope='ACTUAL_MATURE_MATCHED6vs24OPENING16PLY',runs=runs,calls=calls)
 if state!='COMPLETE':result['error']=error
 adapter.atomic_json(OUT/'controller.json',result)
 status=dict(status=state,physical_games=len(calls),training_games=sum(c['context']['phase']=='train' for c in calls),heldout_games=sum(c['context']['phase']=='heldout' for c in calls),wall_seconds=time.monotonic()-started,cap=16,deadline_seconds=600,process_reuse='same profile block only; full fiveleaf readback and ucinewgame each game',old_Task121_not_extended=True)
 if state!='COMPLETE':status['error']=error
 adapter.atomic_json(OUT/'status.json',status);print(json.dumps(status));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())