"""New domain-based coordinate schedule, fixed before any new games."""
import importlib.util,json,math,random,time,sys,hashlib,copy
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task129'
s=importlib.util.spec_from_file_location('deploy127for129',ROOT/'results/dev_aux/task127/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.adapter;G=M.G
s=importlib.util.spec_from_file_location('e108for129',ROOT/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
STEPS=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)]

def execute():
 stop=lambda:A.stop_check(ROOT);stop();binary,digest,q=A.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json')
 if (OUT/'events.jsonl').exists():raise FileExistsError('No rerun or extension')
 journal=A.Journal(OUT/'events.jsonl');started=time.monotonic();deadline=started+900;calls=[];runs=[];e=None
 def block(w,seed,sweep,coordinate,arm,phase):
  nonlocal e
  A.guard(deadline,stop)
  if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:raise RuntimeError('Binary changed')
  e=A.UCI(binary,ROOT,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest;rewards=[]
  try:
   for oi in range(8):
    for color in (True,False):
     opening_seed=87000+(sweep*4+coordinate)*8+oi if phase=='train' else 89000+oi
     random_seed=97000+(sweep*4+coordinate)*8+oi if phase=='train' else 99000+oi
     x=dict(opening_seed=opening_seed,random_seed=random_seed,agent_color=color,phase=phase,name=f's{seed}-{phase}-sweep{sweep}-k{coordinate}-a{arm}-o{oi}-c{int(color)}')
     r=A.play_game(e,w,x,deadline,OUT/'variant.ini',journal,lambda seed:G.opening(seed,plies=24),G.score,stop,cap=16);A.guard(deadline,stop);calls.append(dict(context=x,weights=dict(w),result=r));rewards.append(r['reward'])
     if len(calls)%48==0:
      A.atomic_json(OUT/'progress.json',dict(games=len(calls),wall_seconds=time.monotonic()-started,current=x['name']));print(json.dumps(dict(games=len(calls),wall_seconds=round(time.monotonic()-started,3))),flush=True)
  finally:e.close();e=None
  return rewards
 try:
  for seed in (103,104,105):
   theta=E.starts(seed);run=dict(seed=seed,initial_weights=E.weights(theta),updates=[],heldout=[]);runs.append(run)
   for sweep,step in enumerate(STEPS):
    for k in range(4):
     candidates=[theta[:],theta[:],theta[:]]
     candidates[1][k]=min(E.HIGH,theta[k]+step);candidates[2][k]=max(E.LOW,theta[k]-step)
     groups=[block(E.weights(t),seed,sweep,k,a,'train') for a,t in enumerate(candidates)]
     means=[sum(z)/16 for z in groups];choice=E.select(means);before=E.weights(theta);theta=candidates[choice][:]
     run['updates'].append(dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=before,candidate_weights=[E.weights(t) for t in candidates],means=means,rewards=groups,selected=choice,after=E.weights(theta)))
   run['final_weights']=E.weights(theta)
   for arm in ('initial','final'):
    rs=block(run[arm+'_weights'],seed,0,0,arm,'heldout');run['heldout']+= [dict(arm=arm,opening_index=i//2,color=i%2==0,reward=r) for i,r in enumerate(rs)]
   A.atomic_json(OUT/'partial.json',dict(completed=False,runs=runs,calls=calls))
  state='COMPLETE'
 except BaseException as err:state='INTERRUPTED';error=type(err).__name__+': '+str(err)
 finally:
  if e:e.close()
  journal.close()
 result=dict(completed=state=='COMPLETE',scope='Actual full-domain coordinate schedule, not extension of old frozen experiments',runs=runs,calls=calls)
 if state!='COMPLETE':result['error']=error
 A.atomic_json(OUT/'controller.json',result)
 status=dict(status=state,games=len(calls),training_games=sum(c['context']['phase']=='train' for c in calls),heldout_games=sum(c['context']['phase']=='heldout' for c in calls),wall_seconds=time.monotonic()-started,hard_seconds=900,cap=16,steps=STEPS,no_human_price_in_training=True,old_records_unchanged=True)
 if state!='COMPLETE':status['error']=error
 A.atomic_json(OUT/'status.json',status);print(json.dumps(status));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())