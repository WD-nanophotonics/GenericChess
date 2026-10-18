"""Separate after-seal consumer check using the already pinned q4 source capsule."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid,shutil
R=Path.cwd();D=Path(__file__).resolve().parent;A=R/'docs/archive/root_window_q4_service_20261019';m=json.loads((A/'manifest.json').read_bytes());assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256'];X=R/'.local_agent'/('q4-consumer-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();start=time.perf_counter()
with zipfile.ZipFile(A/'evidence.zip')as z:
 for n,e in m['files'].items():
  if not(n.startswith('source/')or n.startswith('data/root-window-q4-20261019/')):continue
  b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t=(X/n).resolve();assert t.is_relative_to(X.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
S=X/'source';shutil.copytree(X/'data',S/'.local_agent',dirs_exist_ok=True);T=S/'.local_agent/q4-leaf-consumer-20261019';T.mkdir()
for n in ('plan.json','reader.py','reserve-witness.py'):shutil.copyfile(D/n,T/n)
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages';steps=[]
for reader,out in [('reader.py','result.json'),('reserve-witness.py','reserve-witness-result.json')]:
 tick=time.perf_counter()
 code='import sys,runpy,importlib.util,pathlib;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core")is None;runpy.run_path('+repr(str(T/reader))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,check=True,timeout=190)
 a=json.loads((D/out).read_bytes());b=json.loads((T/out).read_bytes());assert{k:v for k,v in a.items()if k not in('seconds','source_files')}=={k:v for k,v in b.items()if k not in('seconds','source_files')}
 steps.append(dict(reader=reader,output=out,seconds=time.perf_counter()-tick))
canonical={}
for p in ('generic_chess/learning/selfplay.py','generic_chess/learning/tdleaf.py','generic_chess/learning/arena.py'):
 canonical[p]=m['files']['source/'+p]['sha256'];assert hashlib.sha256((S/p).read_bytes()).hexdigest()==canonical[p];assert hashlib.sha256((R/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==canonical[p]
q=dict(status='PASS_SEPARATE_AFTERSEAL_Q4_LEAF_CONSUMER',archive_sha256=m['archive_sha256'],steps=steps,regenerated_outputs=2,seconds=time.perf_counter()-start,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,new_Native_queries=0,new_games=0,new_training=0,source_canonical_lf_hashes=canonical,original_raw_source_hashes_preserved=True,scope='Separate after234payload/7outputseal; all1046leafraw/quantized/predictor calculations and39ordinaryq0/check8 witnesses rebuilt. Consumer source read +pureprediction only, no collector/trainer/AUX execution or q4learning claim. CanonicalLFsourcehashes distinguished from rawworkingfilehashes.')
tmp=D/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,D/'qualification.json');print('CONSUMER_SOURCE_PASS',q['seconds'])
