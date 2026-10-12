"""New domain-based coordinate schedule, fixed before any new games."""
import importlib.util,json,math,random,time,sys,hashlib,copy
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task131'
s=importlib.util.spec_from_file_location('deploy127for129',ROOT/'results/dev_aux/task127/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.adapter;G=M.G
s=importlib.util.spec_from_file_location('e108for129',ROOT/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
STEPS=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)]
DECL=json.loads((OUT/'declaration.json').read_bytes());FIXTURES=json.loads((OUT/'opening_contract.json').read_bytes());CACHE=json.loads((ROOT/'results/dev_aux/task129/controller.json').read_bytes())['calls']

def execute():
 stop=lambda:A.stop_check(ROOT);stop();assert hashlib.sha256((ROOT/'results/dev_aux/task129/controller.json').read_bytes()).hexdigest()==DECL['source_controller_sha256'];assert hashlib.sha256((ROOT/'results/dev_aux/task129/run.py').read_bytes()).hexdigest()==DECL['source_driver_sha256'];binary,digest,q=A.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json')
 if (OUT/'events.jsonl').exists():raise FileExistsError('No rerun or extension')
 journal=A.Journal(OUT/'events.jsonl');started=time.monotonic();deadline=started+DECL['new_run_budget_seconds'];calls=[];runs=[];e=None;new_physical=0;excluded=0;cached_used=0
 def block(w,seed,sweep,coordinate,arm,phase):
  nonlocal e,new_physical,excluded,cached_used
  A.guard(deadline,stop);rewards=[]
  if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:raise RuntimeError('Binary changed')
  try:
   for oi in range(8):
    for color in (True,False):
     A.guard(deadline,stop)
     opening_seed=87000+(sweep*4+coordinate)*8+oi if phase=='train' else 89000+oi
     random_seed=97000+(sweep*4+coordinate)*8+oi if phase=='train' else 99000+oi
     x=dict(opening_seed=opening_seed,random_seed=random_seed,agent_color=color,phase=phase,name=f's{seed}-{phase}-sweep{sweep}-k{coordinate}-a{arm}-o{oi}-c{int(color)}')
     fixture=FIXTURES[str(opening_seed)]
     if fixture['terminal']:
      excluded+=1;calls.append(dict(context=x,weights=dict(w),result=None,status='EXCLUDED_INPUT',selection_contribution=0,opening=fixture['moves'],root_termination=fixture['termination']))
      journal.record('excluded_terminal_opening',context=x,weights=w,fixture=fixture);rewards.append(0)
     elif cached_used<len(CACHE):
      c=CACHE[cached_used];assert c['context']==x and c['weights']==w and c['result']['opening']==fixture['moves']
      calls.append(dict(copy.deepcopy(c),provenance='CACHED_ACTUAL_TASK129',source_call_index=cached_used));rewards.append(c['result']['reward'])
      journal.record('cached_actual_callback',context=x,source_call_index=cached_used,source_controller_sha256=DECL['source_controller_sha256']);cached_used+=1
     else:
      if e is None:e=A.UCI(binary,ROOT,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
      r=A.play_game(e,w,x,deadline,OUT/'variant.ini',journal,lambda seed:FIXTURES[str(seed)]['moves'],G.score,stop,cap=16);A.guard(deadline,stop)
      new_physical+=1;calls.append(dict(context=x,weights=dict(w),result=r,provenance='NEW_ACTUAL_TASK131'));rewards.append(r['reward'])
     if len(calls)%48==0:
      A.atomic_json(OUT/'progress.json',dict(trial_slots=len(calls),cached_used=cached_used,new_physical=new_physical,excluded=excluded,wall_seconds=time.monotonic()-started,current=x['name']))
      print(json.dumps(dict(trial_slots=len(calls),cached_used=cached_used,new_physical=new_physical,excluded=excluded,wall_seconds=round(time.monotonic()-started,3))),flush=True)
  finally:
   if e:e.close();e=None
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
 result=dict(completed=state=='COMPLETE',scope='Changed terminal-input contract; includes provenance-bound old actual prefix, old failure preserved',runs=runs,calls=calls)
 if state!='COMPLETE':result['error']=error
 A.atomic_json(OUT/'controller.json',result)
 status=dict(status=state,trial_slots=len(calls),training_games=sum(c['context']['phase']=='train' for c in calls),heldout_games=sum(c['context']['phase']=='heldout' for c in calls),wall_seconds=time.monotonic()-started,hard_seconds=DECL['new_run_budget_seconds'],old_run_seconds=DECL['old_actual_seconds'],inclusive_old_new_run_seconds=DECL['old_actual_seconds']+time.monotonic()-started,cached_actual=cached_used,new_actual=new_physical,excluded_input_slots=excluded,unique_actual_games=cached_used+new_physical,cap=16,steps=STEPS,no_human_price_in_training=True,old_records_unchanged=True)
 if state!='COMPLETE':status['error']=error
 A.atomic_json(OUT/'status.json',status);print(json.dumps(status));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())