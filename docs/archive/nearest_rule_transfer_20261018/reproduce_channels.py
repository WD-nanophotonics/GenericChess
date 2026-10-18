"""Qualify later channel diagnostics against the same immutable backend source."""
from pathlib import Path
import json,zipfile,hashlib,uuid,shutil,subprocess,sys,os,time
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;PUBLIC=R/'docs/research/data/nearest_rule_transfer_20261018';P=R/'docs/archive/movement_price_transfer_20261017/evidence.zip';X=R/'.local_agent'/('channel-source-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();start=time.perf_counter();m=json.loads((O/'manifest.json').read_bytes());assert hashlib.sha256(P.read_bytes()).hexdigest()==m['parent_source']['sha256']
with zipfile.ZipFile(P)as z:
 parent=json.loads(z.read('manifest.json'))
 for n,e in parent['files'].items():
  if not n.startswith('source/'):continue
  b=z.read(n);assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'];p=(X/n).resolve();assert p.is_relative_to(X.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
S=X/'source';D=S/'.local_agent/nearest-rule-transfer-20261017';D.mkdir(parents=True);pins={};expected={}
for n in ['coupling-plan.json','coupling-inputs.json','coupling.py','coupling-result.json','coupling-factorial.py','coupling-factorial-result.json']:
 b=(PUBLIC/n).read_bytes();pins[n]=hashlib.sha256(b).hexdigest();(D/n).write_bytes(b)
for n in ['coupling-result.json','coupling-factorial-result.json']:
 expected[n]=json.loads((D/n).read_bytes());(D/n).rename(D/(n+'.sealed-original'))
env=dict(os.environ);env['GC_REPLAY_STOP_ROOT']=str(R);env['PYTHONPATH']='';site=Path(sys.prefix)/'Lib/site-packages';steps=[]
for script in ['coupling.py','coupling-factorial.py']:
 t=time.perf_counter();code='import sys,pathlib,runpy,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(D/script))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 with(X/(script+'.log')).open('w',encoding='utf-8')as f:subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=190)
 steps.append(dict(script=script,seconds=time.perf_counter()-t,exit_code=0))
def clean(x):
 if isinstance(x,dict):return {k:clean(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return [clean(v)for v in x]
 return x
for n,v in expected.items():assert clean(v)==clean(json.loads((D/n).read_bytes())),n
q=dict(status='PASS_BOTH_CHANNEL_OUTPUTS_EXTRACTED_SOURCE',payload_sha256=pins,source_parent_sha256=m['parent_source']['sha256'],both_outputs_parked_before_regeneration=True,all_non_time_fields_equal=True,native_absent=True,python_S_extracted_origins=True,real_primary_stop_root=True,new_fitness_games=0,new_training=0,steps=steps,seconds=time.perf_counter()-start,scope='Separate post-seal64input six/tenobjective scientific diagnostics; not silently part of original35payloadcapsule. OriginalSIXwordingscopeerratum applies toactualtenobjectivefactorial data. No promotionutility or all-domainclaim.')
tmp=PUBLIC/'channel-qualification.tmp';tmp.write_text(json.dumps(q,indent=2)+'\n',encoding='utf-8');os.replace(tmp,PUBLIC/'channel-qualification.json');print(q,flush=True)
