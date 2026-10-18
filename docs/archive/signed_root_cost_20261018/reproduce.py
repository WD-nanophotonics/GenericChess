"""Pinned-source no-Native rebuild of saved complete-state/cost receipts."""
from pathlib import Path
import json,hashlib,zipfile,sys,subprocess,os,time,shutil,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;X=R/'.local_agent'/('signed-cost-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();start=time.perf_counter();steps=[]
def extract(p,target):
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None;m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t=(target/n).resolve();assert t.is_relative_to(target.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 return m
m=extract(O/'evidence.zip',X)
for dep in m['dependencies']:
 p=(O/dep['path']).resolve();assert hashlib.sha256(p.read_bytes()).hexdigest()==dep['sha256'];extract(p,X/dep['target'])
S=X/'parent/source';shutil.copyfile(X/'prior-product/product/generic_chess/core/transition.py',S/'generic_chess/core/transition.py')
for n in('generic_chess/native/semantic_engine.py',):
 t=S/n;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(X/'product'/n,t)
shutil.copytree(X/'data',S/'.local_agent',dirs_exist_ok=True)
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages';expected={}
def poll():
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused')),'EXPLICIT_STOP'
def run(dn,outputs):
 for name in outputs:
  p=S/'.local_agent'/dn/name;source_name=next(x for x in m['rebuild_steps']if x['directory']==dn).get('expected_sources',{}).get(name,name);ep=p.with_name(source_name);expected[dn,name]=json.loads(ep.read_bytes());
  if p.exists():p.rename(p.with_name(name+'.sealed-original'))
 poll();tick=time.perf_counter();p=S/'.local_agent'/dn/'reader.py'
 code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(p))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 with(X/(dn+'.log')).open('w',encoding='utf8')as log:
  proc=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   try:poll();assert time.perf_counter()-tick<1250,'SOURCE_READER_CAP'
   except BaseException:proc.terminate();proc.wait();raise
   time.sleep(.25)
  assert proc.returncode==0,(dn,proc.returncode,str(X))
 steps.append(dict(directory=dn,seconds=time.perf_counter()-tick));print('SIGNED_COST_QUALIFIED',steps[-1],flush=True)
for item in m['rebuild_steps']:run(item['directory'],item['outputs'])
for(directory,name),expected_value in expected.items():
 actual=json.loads((S/'.local_agent'/directory/name).read_bytes())
 if name=='reader-result.json':actual={k:v for k,v in actual.items()if k!='seconds'};expected_value={k:v for k,v in expected_value.items()if k!='seconds'}
 assert actual==expected_value,(directory,name)
q=dict(status='PASS_SEALED_SIGNED_COST_AND_FULL_CORE',payloads=len(m['files']),regenerated_outputs=len(expected),steps=steps,seconds=time.perf_counter()-start,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,new_Native_queries=0,new_games=0,new_generation=0,new_training=0,scope='Fullsignedparent/PV/checkpoint/costreceipts,wide72continuations/parents/PV,12typedprofiles,actualprojectionallfields/source-delta, andONLYclosedwideCoreD2frontiers frompinnedsources. No cappedtailrefill, Native/timing rerun, externalrules/WDL/learning/populationproof.')
tmp=O/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,O/'qualification.json');print('SIGNED_COST_SOURCE_PASS',q['seconds'],flush=True)
