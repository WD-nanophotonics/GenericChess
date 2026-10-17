from pathlib import Path
import json,hashlib,zipfile,sys,os,subprocess,time,shutil
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/rule-aware-utility-20261017';O=R/'docs/archive/rule_A_mapping_20261017';X=D/'fresh';X.mkdir();started=time.perf_counter()
with zipfile.ZipFile(O/'evidence.zip')as z:
 m=json.loads(z.read('manifest.json'))
 for n,e in m['files'].items():
  p=(X/n).resolve();assert p.is_relative_to(X.resolve());b=z.read(n);assert hashlib.sha256(b).hexdigest()==e['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
dep=m['source_dependency'];assert hashlib.sha256((R/dep['path']).read_bytes()).hexdigest()==dep['sha256'];S=X/'source'
with zipfile.ZipFile(R/dep['path'])as z:
 parent=json.loads(z.read('manifest.json'));source_files=0
 for n,e in parent['files'].items():
  if not n.startswith('source/'):continue
  p=(X/n).resolve();assert p.is_relative_to(X.resolve());b=z.read(n);assert hashlib.sha256(b).hexdigest()==e['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);source_files+=1
M=S/'.local_agent/rule-aware-utility-20261017';M.mkdir(parents=True)
for kind in ['data/utility','analysis/utility']:
 for p in (X/kind).iterdir():shutil.copyfile(p,M/p.name)
expected={}
for n in ['reader-result.json','analysis.json']:
 p=M/n;expected[n]=json.loads(p.read_bytes());p.rename(p.with_name(n+'.sealed-original'))
env=dict(os.environ,PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',GC_REPLAY_STOP_ROOT=str(R));steps=[]
for n,cap in [('reader.py',700),('analyze.py',120)]:
 code='import sys,pathlib,runpy,importlib.util;sys.path[:0]='+repr([str(S),str(R/'.venv/Lib/site-packages')])+';assert importlib.util.find_spec("generic_chess._native_core")is None;sys.argv=['+repr(str(M/n))+'];runpy.run_path('+repr(str(M/n))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None));'
 begin=time.perf_counter()
 with(D/('fresh-'+n+'.log')).open('w')as log:
  c=subprocess.Popen([str(R/'.venv/Scripts/python.exe'),'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT)
  while c.poll()is None:
   try:
    assert time.perf_counter()-begin<cap,'FROZEN_SOURCE_STAGE_CAP'
    for name in ['rollout','advisor','slack']:
     f=json.loads((R/'.local_agent'/(name+'.json')).read_bytes());assert not f.get('user_paused')and not f.get('stopped')
   except BaseException:c.terminate();c.wait();raise
   time.sleep(.25)
  assert c.returncode==0,(n,c.returncode)
 steps.append(dict(name=n,seconds=time.perf_counter()-begin,exit_code=0));print('QUALIFIED',steps[-1],flush=True)
def strip(x):
 if isinstance(x,dict):return {k:strip(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return [strip(v)for v in x]
 return x
for n,old in expected.items():assert strip(old)==strip(json.loads((M/n).read_bytes())),n
q=json.loads((O/'qualification.json').read_bytes());q.update(status='PASS_ADAPTIVE_RECORDS_AND_ANALYSIS_FRESH_PINNED_SOURCE',source_dependency_files=source_files,own_outputs_parked_before_regeneration=2,all_non_time_fields_equal=True,recorded_original_costs_equal=True,python_S_extracted_origins=True,Native_absent_for_Core=True,real_primary_stops=True,new_fitness_games=0,new_training=0,steps=steps,seconds=time.perf_counter()-started,scope='Ownthinarchivehash+parentchecksum/sourcefilehashesverified; onlyparentsourcehydrated, nooriginalparentfitness or91/92TRAIN/EVALrerun. Fullnew3264Corehistory/PVreader andphysicalboundanalysisactuallyregenerated. Existingtestedbd805Cconsumercontract notrebuiltorre-executed here; no claim186parentmembers newlyregenerated.')
(O/'qualification.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());write_json(D/'fresh-qualification.json',q);print('ADAPTIVE_FRESH_PASS',q['seconds'],flush=True)
