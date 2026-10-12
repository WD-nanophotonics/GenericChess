"""One bounded matchedsamebinary alignmentbatch; freeze allends beforeheldout."""
import json,math,time,sys,importlib.util,hashlib,datetime
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task152'
s=importlib.util.spec_from_file_location('toggle139for140',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.A;G=M.M.G
s=importlib.util.spec_from_file_location('e108for140',R/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
D=json.loads((O/'declaration.json').read_bytes());assert json.loads((O/'qualification.json').read_bytes())['complete'];F=json.loads((O/'fixtures.json').read_bytes());BASE=A.configure
def prepare(e,w,config,deadline,stop,clock=time.monotonic):
 probes=BASE(e,w,config,deadline,stop,clock)
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();ack=[x for x in reply if x.startswith('info string DEV_AUX alignment ')]
 if len(ack)!=1:raise ValueError('missingtableack')
 parts=ack[0].split();assert int(parts[4])==e.alignment
 measured={int(p.split(':')[0]):tuple(map(int,p.split(':')[1:])) for p in parts[5:]};mg=[126,781,825,1276,2538];eg=[208,854,915,1380,2682]
 expected={i+1:((w[k],w[k]) if e.alignment else (mg[i],eg[i])) for i,k in enumerate('PNBRQ')}
 if measured!=expected:raise ValueError('searchtablemismatch')
 e.last_table_ack=ack[0];e.send('ucinewgame');e.ready();return probes
A.configure=prepare
def execute():
 def stop():
  for root in (R,R.parent/'GenericChess 2'):
   for name in ('rollout','advisor','slack'):
    p=root/f'.local_agent/{name}.json'
    for attempt in range(3):
     try:
      value=json.loads(p.read_bytes())
      if not isinstance(value,dict):raise ValueError('stop-state notobject:'+str(p))
      if value.get('user_paused') or value.get('stopped'):raise A.PersistentStop('persistentuserstop:'+str(p))
      break
     except (json.JSONDecodeError,OSError) as ex:
      with (R/'.local_agent/material-mode3/flag-read-recovery.jsonl').open('a',encoding='utf-8') as recovery:
       recovery.write(json.dumps(dict(path=str(p),attempt=attempt,error=type(ex).__name__+': '+str(ex),at=datetime.datetime.now(datetime.timezone.utc).isoformat()))+'\n')
      if attempt==2:raise RuntimeError('unreadablestopafter3attempts:'+str(p)) from ex
      time.sleep(.05)
 stop();assert hashlib.sha256((O/'fixtures.json').read_bytes()).hexdigest()==D['fixtures_sha256']
 binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256']
 if (O/'events.jsonl').exists():raise FileExistsError('frozenbatchcannotrerun')
 started=time.monotonic();deadline=started+D['deadline_seconds'];j=A.Journal(O/'events.jsonl');calls=[];runs=[];e=None;new=excluded=0
 def block(w,seed,aligned,sweep,k,arm,phase):
  nonlocal e,new,excluded
  A.guard(deadline,stop);rs=[]
  try:
   for oi in range(8):
    for color in (True,False):
     A.guard(deadline,stop);offset=(sweep*4+k)*8+oi if phase=='train' else oi
     opening_seed=(2007000 if phase=='train' else 2009000)+offset;random_seed=(2107000 if phase=='train' else 2109000)+offset
     x=dict(opening_seed=opening_seed,random_seed=random_seed,agent_color=color,phase=phase,name=f's{seed}-align{aligned}-{phase}-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}',start_seed=seed,alignment=aligned)
     fixture=F[str(opening_seed)]
     if fixture['terminal']:
      excluded+=1;calls.append(dict(context=x,weights=dict(w),result=None,status='EXCLUDED_INPUT',selection_contribution=0));rs.append(0);j.record('excluded_input',context=x)
     else:
      if e is None:e=M.start(binary,aligned,deadline,stop)
      r=A.play_game(e,w,x,deadline,O/'variant.ini',j,lambda seed:F[str(seed)]['moves'],G.score,stop,cap=16)
      r['search_table_ack']=e.last_table_ack;new+=1;calls.append(dict(context=x,weights=dict(w),result=r,status='ACTUAL'));rs.append(r['reward'])
     if len(calls)%48==0:
      A.atomic_json(O/'progress.json',dict(slots=len(calls),games=new,excluded=excluded,seconds=time.monotonic()-started,current=x['name']))
      print(json.dumps(dict(slots=len(calls),games=new,seconds=round(time.monotonic()-started,2))),flush=True)
  finally:
   if e:e.close();e=None
  return rs
 try:
  for seed,aligned in D['seed_alignment_order']:
   theta=E.starts(seed);run=dict(seed=seed,alignment=aligned,initial_weights=E.weights(theta),updates=[],heldout=[]);runs.append(run)
   for sweep,step in enumerate(D['steps']):
    for k in range(4):
     candidates=[theta[:],theta[:],theta[:]];candidates[1][k]=min(E.HIGH,theta[k]+step);candidates[2][k]=max(E.LOW,theta[k]-step)
     groups=[block(E.weights(t),seed,aligned,sweep,k,a,'train') for a,t in enumerate(candidates)]
     means=[sum(z)/16 for z in groups];chosen=E.select(means);before=E.weights(theta);theta=candidates[chosen][:]
     run['updates'].append(dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=before,candidate_weights=[E.weights(t) for t in candidates],means=means,rewards=groups,selected=chosen,after=E.weights(theta)))
   run['final_weights']=E.weights(theta);run['endpoint_frozen_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   A.atomic_json(O/'endpoints_partial.json',dict(complete=False,ends=[{k:r[k] for k in ('seed','alignment','initial_weights','final_weights','endpoint_frozen_at')} for r in runs if 'final_weights' in r]))
  freeze_time=datetime.datetime.now(datetime.timezone.utc).isoformat()
  A.atomic_json(O/'endpoints.json',dict(complete=True,all_endpoints_frozen_at=freeze_time,training_calls=len(calls),ends=[{k:r[k] for k in ('seed','alignment','initial_weights','final_weights','endpoint_frozen_at')} for r in runs]))
  # No training/selection after ANYheldout callback.
  for run in runs:
   for arm in ('initial','final'):
    rs=block(run[arm+'_weights'],run['seed'],run['alignment'],0,0,arm,'heldout')
    run['heldout'] += [dict(arm=arm,opening_index=i//2,color=i%2==0,reward=r) for i,r in enumerate(rs)]
  state='COMPLETE'
 except BaseException as ex:state='INTERRUPTED';error=type(ex).__name__+': '+str(ex)
 finally:
  if e:e.close()
  j.close()
 out=dict(completed=state=='COMPLETE',runs=runs,calls=calls,global_endpoint_freeze_at=locals().get('freeze_time'),scope='Samebinaryalignmentprice-family intervention, fixedshortobjective; allstartends beforeheldout.')
 if state!='COMPLETE':out['error']=error
 A.atomic_json(O/'controller.json',out);status=dict(status=state,slots=len(calls),actual_games=new,excluded_input_slots=excluded,train_games=sum(c['context']['phase']=='train' and c['result'] is not None for c in calls),heldout_games=sum(c['context']['phase']=='heldout' and c['result'] is not None for c in calls),wall_seconds=time.monotonic()-started,hard_seconds=D['deadline_seconds'],binary_sha256=D['binary_sha256'],cap=16,allends_beforeheldout=locals().get('freeze_time') is not None,nohumanfit=True)
 if state!='COMPLETE':status['error']=error
 A.atomic_json(O/'status.json',status);print(json.dumps(status));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())
