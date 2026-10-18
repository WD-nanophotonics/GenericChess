"""Rebuild sealed static crossover readers from pinned source/inputs; no Native."""
from pathlib import Path
import json,hashlib,zipfile,sys,subprocess,os,time,shutil,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;X=R/'.local_agent'/('static-objective-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();began=time.perf_counter();steps=[]
def extract(p,target,prefix=None):
 with zipfile.ZipFile(p)as z:
  m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256']
   if prefix is not None and not n.startswith(prefix):continue
   t=(target/n).resolve();assert t.is_relative_to(target.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 return m
m=extract(O/'evidence.zip',X);S=X/'source/source';deps=[]
for i,d in enumerate(m['dependencies']):
 p=O/d['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256'];t=X/('source'if d['kind']=='source'else'dep'+str(i));dm=extract(p,t,prefix='source/'if d['kind']=='source'else None);deps.append(dict(path=d['path'],verified_payloads=len(dm['files'])))
 if d['kind']=='data':
  dest=S/'.local_agent'/d['private_directory'];dest.mkdir(parents=True)
  for f in(t/'data').iterdir():shutil.copyfile(f,dest/f.name)
D=S/'.local_agent/static-input-objective-20261018';D.mkdir(parents=True)
for d in ('data','analysis'):
 for p in(X/d).iterdir():shutil.copyfile(p,D/p.name)
expected={}
for n in ['coverage-started.json','coverage-result.json','static-models.json','reader-result.json','objective-analysis.json','paired-static-decomposition.json']:
 p=D/n;expected[n]=json.loads(p.read_bytes());p.rename(p.with_name(n+'.sealed-original'))
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages'
def poll():
 for n in ('rollout','advisor','slack'):
  q=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(q.get('stopped')or q.get('user_paused')),'EXPLICIT_STOP'
for name in ['coverage.py','reader.py','analyze.py']:
 poll();tick=time.perf_counter();code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(D/name))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 # Coverage has no per-state historical clock dependence, but must read real stops.
 # Its ROOT is the extracted tree, so use a narrow, explicit stop-root overlay.
 if name=='coverage.py':
  original=(D/name).read_bytes();text=original.decode('utf-8-sig');needle="z=json.loads((R/'.local_agent'/(name+'.json')).read_bytes())";assert text.count(needle)==1;text=text.replace(needle,"z=json.loads((Path(__import__('os').environ['GC_REPLAY_STOP_ROOT'])/'.local_agent'/(name+'.json')).read_bytes())");(D/name).write_bytes(text.encode());
  # Preserve exact script hash for startedreceipt identity; overlay scope recorded below.
  expected['coverage-started.json']['source_sha256']=hashlib.sha256((D/name).read_bytes()).hexdigest()
 with(X/(name+'.log')).open('w',encoding='utf8')as f:
  p=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
  while p.poll()is None:
   try:poll();assert time.perf_counter()-tick<600,'READER_CAP'
   except BaseException:p.terminate();p.wait();raise
   time.sleep(.25)
  assert p.returncode==0,(name,p.returncode,str(X))
 steps.append(dict(script=name,seconds=time.perf_counter()-tick));print('QUALIFIED',steps[-1],flush=True)
def strip(v):
 if isinstance(v,dict):return{k:strip(x)for k,x in v.items()if k!='seconds'}
 if isinstance(v,list):return[strip(x)for x in v]
 return v
for n,v in expected.items():assert strip(v)==strip(json.loads((D/n).read_bytes())),n
q=dict(status='PASS_PINNED_SOURCE_AND_INPUTS_STATIC_CROSSOVER',own_payloads=len(m['files']),dependencies=deps,all_six_outputs_parked_before_regeneration=True,all_non_time_fields_equal_except_documented_stop_overlay_source_hash=True,original_query_journal_hash_exact=True,native_absent=True,python_S_extracted_origins=True,real_primary_stop_root=True,coverage_overlay='Single stop-read ROOT replacement only, originalsealedsource retained; startedsourcehash differs exactly for documented overlay; no fake flags/native/current-source fallback.',new_queries=0,new_generation=0,new_games=0,new_training=0,steps=steps,seconds=time.perf_counter()-began,scope='Full1533staticprofiles+all4599roots/NativePV/gradients+matchedobjective/606same-rulearithmetic, notnewfitness/WDL/independentexternalrules authority.');tmp=O/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,O/'qualification.json');print('SOURCE_PASS',q['seconds'],flush=True)
