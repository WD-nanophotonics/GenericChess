"""Reconstruct sealed readers; never execute fitness or training producers."""
from pathlib import Path
import hashlib,json,zipfile,sys,subprocess,os,time,shutil,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;P=R/'docs/archive/movement_price_transfer_20261017/evidence.zip';X=R/'.local_agent'/('filter-source-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();began=time.perf_counter();steps=[]
def extract(zpath,target,prefix=None):
 with zipfile.ZipFile(zpath) as z:
  m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   b=z.read(n);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
   if prefix is not None and not n.startswith(prefix):continue
   p=(target/n).resolve();assert p.is_relative_to(target.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
 return m
m=extract(O/'evidence.zip',X);assert hashlib.sha256(P.read_bytes()).hexdigest()==m['parent_source']['sha256'];parent=extract(P,X/'parent',prefix='source/');S=X/'parent/source';D=S/'.local_agent/playability-filter-20261018';D.mkdir(parents=True)
for p in (X/'data').iterdir():shutil.copyfile(p,D/p.name)
for p in (X/'analysis').iterdir():shutil.copyfile(p,D/p.name)
expected={}
for n in ['reader-result.json','analysis.json','opportunity-result.json']:
 p=D/n;expected[n]=json.loads(p.read_bytes());p.rename(p.with_name(n+'.sealed-original'))
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages'
def poll():
 for name in ('rollout','advisor','slack'):
  p=R/'.local_agent'/(name+'.json');f=json.loads(p.read_bytes());assert not f.get('user_paused') and not f.get('stopped'),'EXPLICIT_STOP'
for name,cap in [('reader.py',600),('analyze.py',120),('opportunity.py',600)]:
 poll();start=time.perf_counter();code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(D/name))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+')) for k,v in sys.modules.items() if k.startswith("generic_chess") and getattr(v,"__file__",None))'
 with (X/(name+'.log')).open('w',encoding='utf-8') as f:
  child=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
  while child.poll() is None:
   try:poll();assert time.perf_counter()-start<cap,'FROZEN_READER_CAP'
   except BaseException:child.terminate();child.wait();raise
   time.sleep(.25)
  assert child.returncode==0,(name,child.returncode,str(X))
 steps.append(dict(script=name,seconds=time.perf_counter()-start,exit_code=0));print('QUALIFIED',steps[-1],flush=True)
def strip(x):
 if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k!='seconds'}
 if isinstance(x,list):return [strip(v) for v in x]
 return x
for n,old in expected.items():assert strip(old)==strip(json.loads((D/n).read_bytes())),n
q=json.loads((O/'qualification.json').read_bytes());q.update(status='PASS_FILTER_EXTRACTED_SOURCE_THREE_OUTPUTS_REGENERATED',own_payloads_hash_verified=len(m['files']),parent_source_payloads_hash_verified=sum(n.startswith('source/') for n in parent['files']),all_derived_outputs_parked_before_regeneration=True,all_non_time_fields_equal=True,original_query_clock_fields_compare_exactly=True,python_S_extracted_origins=True,native_absent=True,real_primary_stop_root=True,new_fitness_games=0,new_training=0,steps=steps,seconds=time.perf_counter()-began,scope='Core fullstate/history/ALLchildfeature reconstruction, linkedgenerationpairs and posthoc terminalawareopportunities; not independentWDL/rulesauthority or oldtraining reexecution. Parent source fixed bySHA. No fakeflags or liveeditable fallback.')
tmp=O/'qualification.tmp';tmp.write_text(json.dumps(q,indent=2)+'\n',encoding='utf-8');os.replace(tmp,O/'qualification.json');print('SOURCE_PASS',q['seconds'],flush=True)
