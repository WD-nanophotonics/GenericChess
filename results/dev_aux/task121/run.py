"""Distinct frozen16ply mature learning experiment; no result-dependent extension."""
import hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'results/dev_aux/task109'));import adapter

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
GAME=load('short104_actual16',ROOT/'results/dev_aux/task104/short_game.py')
EVO=load('evolution108_actual16',ROOT/'results/dev_aux/task108/evolution.py')
BINARY=ROOT/'.local_agent/material-selfplay/fairy-material.exe';QUAL=ROOT/'results/dev_aux/task120/qualification.json'

def execute():
 stop=lambda:adapter.stop_check(ROOT);stop()
 binary,digest,q=adapter.validated_entry(BINARY,QUAL)
 pilot_path=ROOT/'results/dev_aux/task120/pilot16/pilot.json';pilot=json.loads(pilot_path.read_bytes());status=json.loads(pilot_path.with_name('status.json').read_bytes())
 if pilot.get('scope')!='REAL_QUALIFIED_MATURE' or not pilot.get('complete'):raise RuntimeError('Actual qualified pilot required')
 if not EVO.pilot_informative(pilot['rows']):raise RuntimeError('Actual paired pilot lacks signal')
 projected=status['wall_seconds']/4*480
 if projected>900:raise RuntimeError('Inclusive pilot cost projection exceeds declared900s stage')
 if (OUT/'events.jsonl').exists():raise FileExistsError('No rerun/resume of this frozen stage')
 journal=adapter.Journal(OUT/'events.jsonl');counts={'train':0,'heldout':0};started=time.monotonic()
 def game(weights,context,deadline):
  adapter.guard(deadline,stop)
  if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:raise RuntimeError('Qualified binary changed')
  engine=None
  try:
   engine=adapter.UCI(binary,ROOT,deadline,stop);engine.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
   result=adapter.play_game(engine,weights,context,deadline,OUT/'variant.ini',journal,GAME.opening,GAME.score,stop,cap=16)
   counts[context['phase']]+=1
  finally:
   if engine:engine.close()
  adapter.guard(deadline,stop)
  adapter.atomic_json(OUT/'progress.json',dict(physical_completed_by_phase=counts,wall_seconds=time.monotonic()-started,current=context['name']))
  if sum(counts.values())%24==0:print(json.dumps(dict(physical_completed=sum(counts.values()),wall_seconds=round(time.monotonic()-started,3))),flush=True)
  return result
 controller=EVO.Experiment(game,stop=stop,budget_seconds=900)
 try:
  result=controller.run(pilot['rows']);state='COMPLETE' if result['completed'] else result.get('status','INCOMPLETE')
 except BaseException as err:
  state='INTERRUPTED';result=dict(completed=False,error=type(err).__name__+': '+str(err),runs=controller.runs,calls=controller.calls)
 finally:journal.close()
 adapter.atomic_json(OUT/'controller.json',result)
 summary=dict(status=state,scope='ACTUAL_MATURE_PURE_MATERIAL16PLY',binary_sha256=digest,cap=16,stage_budget_seconds=900,
              physical_completed_by_phase=counts,accepted_callbacks=len(controller.calls),wall_seconds=time.monotonic()-started,pilot_seconds_separate=status['wall_seconds'],projected_480_seconds=projected,
              no_human_values_in_sampling_reward_or_selection=True,no_automatic_extension=True,human_ratio_recovery_not_yet_assessed=True)
 if 'error' in result:summary['error']=result['error']
 adapter.atomic_json(OUT/'status.json',summary);print(json.dumps(summary));return 0 if state=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())