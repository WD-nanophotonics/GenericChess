"""Rebuild recorded arithmetic/Core receipts from sealed sources, never fitness."""
from pathlib import Path
import json,hashlib,zipfile,sys,subprocess,os,time,shutil,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;X=R/'.local_agent'/('root-windows-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();start=time.perf_counter();steps=[]
def extract(p,target,prefix=None):
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None;m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256']
   if prefix is not None and not n.startswith(prefix):continue
   t=(target/n).resolve();assert t.is_relative_to(target.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 return m
m=extract(O/'evidence.zip',X)
for dep in m['dependencies']:
 p=(O/dep['path']).resolve();assert hashlib.sha256(p.read_bytes()).hexdigest()==dep['sha256'];extract(p,X/dep['target'],dep['prefix'])
S=X/'parent/source';shutil.copyfile(X/'product/product/generic_chess/core/transition.py',S/'generic_chess/core/transition.py');shutil.copytree(X/'data',S/'.local_agent',dirs_exist_ok=True)
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages';expected={}
def poll():
 for n in ('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused')),'EXPLICIT_STOP'
def park(dn,files):
 for name in files.split():
  p=S/'.local_agent'/dn/name;expected[dn,name]=json.loads(p.read_bytes());p.rename(p.with_name(name+'.sealed-original'))
def run(dn,script):
 poll();tick=time.perf_counter();p=S/'.local_agent'/dn/script
 code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(p))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 with(X/(dn.replace('/','-')+'-'+script+'.log')).open('w',encoding='utf8')as log:
  proc=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll()is None:
   try:poll();assert time.perf_counter()-tick<900,'READER_CAP'
   except BaseException:proc.terminate();proc.wait();raise
   time.sleep(.25)
  assert proc.returncode==0,(dn,script,proc.returncode,str(X))
 steps.append(dict(directory=dn,script=script,seconds=time.perf_counter()-tick));print('QUALIFIED',steps[-1],flush=True)
for dn,outputs,scripts in [
 ('rank-ratio-d2-20261018','reader-result.json',['reader.py']),
 ('root-window-budget-20261018','reader-result.json analysis.json',['reader.py']),
 ('root-window-stateful-20261018','reader-result.json',['reader.py']),
 ('root-window-utility-20261018','reader-result.json reader-source-files.json analysis.json profile-reader-result.json common-parent-analysis.json coverage.json',['reader.py','analyze.py','profile-reader.py','common-parent-analysis.py','coverage.py']),
 ('root-window-wall-20261018','reader-result.json reader-source-files.json analysis.json profile-reader-result.json common-parent-analysis.json coverage.json deadline-cost.json',['reader.py','analyze.py','profile-reader.py','common-parent-analysis.py','coverage.py','deadline-cost.py']),
 ('root-window-strong-20261018','reader-result.json reader-source-files.json analysis.json profile-reader-result.json common-parent-analysis.json coverage.json symmetry-analysis.json',['reader.py','analyze.py','profile-reader.py','common-parent-analysis.py','coverage.py','symmetry-analysis.py']),
 ('root-window-large-20261018','reader-result.json analysis.json',['reader.py'])]:
 park(dn,outputs)
 for script in scripts:run(dn,script)
for (directory,name),v in expected.items():
 actual=json.loads((S/'.local_agent'/directory/name).read_bytes())
 if name in('reader-result.json','profile-reader-result.json'):
  actual={k:x for k,x in actual.items()if k!='seconds'};v={k:x for k,x in v.items()if k!='seconds'}
 assert actual==v,(directory,name)
q=dict(status='PASS_SEALED_EXACT_ROOT_WINDOWS_CORE_AND_ARITHMETIC',payloads=len(m['files']),regenerated_outputs=len(expected),steps=steps,seconds=time.perf_counter()-start,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,new_Native_queries=0,new_games=0,new_generation=0,new_training=0,scope='AllsavedcompleteCoreD2 references,191persistedcostqueries,192statefulcalls andnew512nodecap/256deadline/128strongfoegame/96largeboard receipts/arithmetic/profile inputs frompinnedparent/exactCoretransition. LostfirstqueryUNKNOWN/unobservedpaidnodes, oldcappedtree notrefilled. Allnonruntimefields equalincludingrecordedcosts. No Native/generation/fitness/training rerun or timing/binary/WDL/externalrules/populationproof.')
tmp=O/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,O/'qualification.json');print('ROOT_WINDOWS_SOURCE_PASS',q['seconds'],flush=True)
