"""Fixed-source no-Native reproduction of q4 service and closed Core controls."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,shutil,time,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;X=R/'.local_agent'/('q4-service-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';start=time.perf_counter();expected={};steps=[]
outer=json.loads((O/'manifest.json').read_bytes());assert hashlib.sha256((O/'evidence.zip').read_bytes()).hexdigest()==outer['archive_sha256']
with zipfile.ZipFile(O/'evidence.zip')as z:
 assert z.testzip()is None;m=json.loads(z.read('manifest.json'))
 for n,e in m['files'].items():
  b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t=(X/n).resolve();assert t.is_relative_to(X.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
shutil.copytree(X/'data',S/'.local_agent',dirs_exist_ok=True)
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages'
def poll():
 for name in ('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(name+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused')),'EXPLICIT_STOP'
for step in m['rebuild_steps']:
 dn=step['directory'];reader=step['reader']
 for name in step['outputs']:
  p=S/'.local_agent'/dn/name
  if p.exists():expected[dn,name]=json.loads(p.read_bytes());p.rename(p.with_name(name+'.sealed-original'))
 poll();tick=time.perf_counter();target=S/'.local_agent'/dn/reader
 code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core")is None;runpy.run_path('+repr(str(target))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 with(X/(reader+'.log')).open('w',encoding='utf8')as log:
  proc=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   try:poll();assert time.perf_counter()-tick<920,'QUALIFICATION_STAGE_CAP'
   except BaseException:proc.terminate();proc.wait();raise
   time.sleep(.25)
  assert proc.returncode==0,(dn,reader,proc.returncode,str(X))
 for name in step['outputs']:
  actual=json.loads((S/'.local_agent'/dn/name).read_bytes())
  if(dn,name)in expected:
   a=expected[dn,name]
   if name in ('reader-result.json','profile-reader-result.json'):a={k:v for k,v in a.items()if k!='seconds'};actual={k:v for k,v in actual.items()if k!='seconds'}
   assert a==actual,(dn,name)
  else:assert actual['status']=='PASS_CLOSED_CORE_Q4_AND_SELECTED_ACTIONS'and len(actual['closed_root_controls'])==30 and len(actual['selected_children'])==2 and len(actual['skipped_original_unknown'])==2
 steps.append(dict(directory=dn,reader=reader,outputs=step['outputs'],seconds=time.perf_counter()-tick));print('Q4_SOURCE_QUALIFIED',steps[-1],flush=True)
q=dict(status='PASS_FIXED_SOURCE_Q4_SERVICE_AND_CLOSED_CORE',payloads=len(m['files']),archive_sha256=outer['archive_sha256'],regenerated_outputs=sum(len(s['outputs'])for s in steps),steps=steps,seconds=time.perf_counter()-start,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,new_Native_queries=0,new_games=0,new_training=0,closed_Core_q4_trees_rebuilt=27,closed_exact_terminal_roots_rebuilt=3,selected_children_rebuilt=2,original_incomplete_Core_roots_not_rerun=[62100608,62101308],scope='Fullsavedserviceinputs/roots/PV/records/UNKNOWN/bounds/returnedqpolicy/cost arithmetic andONLYpreviousclosedCoreq4producttargets fromcapturedsource. Coresearch replay isadditional qualificationwork, notnewfitness ororiginaltiming replication. Noall-action/WDL/all-domain/population/learner proof.')
tmp=O/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,O/'qualification.json');print('Q4_SOURCE_PASS',q['seconds'],flush=True)
