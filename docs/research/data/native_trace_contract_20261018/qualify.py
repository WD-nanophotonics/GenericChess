"""Reproduce only signed Core/PV reader from pinned source, no Native queries."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,os,shutil,time,uuid
R=Path.cwd();D=Path(__file__).resolve().parent;X=R/'.local_agent'/('signed-root-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();start=time.perf_counter();S=X/'source';S.mkdir()
deps=[('movement_price_transfer_20261017','59d7aee577d2d567543cb3a805dbdc0b88227e7cb7f67014ff93373c6b60efb4','source/'),('acquisition_checked_submit_20261018','d29d3b6f4a8bc5f39e399d123bbebf3d8e0baf02c0661cbd2563e493367e3667','product/')]
for name,sha,prefix in deps:
 p=R/'docs/archive'/name/'evidence.zip';assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
 with zipfile.ZipFile(p)as z:
  m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   if not n.startswith(prefix):continue
   b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t=(S/n[len(prefix):]).resolve();assert t.is_relative_to(S.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
T=S/'signed';T.mkdir()
for n in('inputs.json','references.json','queries.jsonl','reader.py','plan.json'):shutil.copyfile(D/n,T/n)
site=Path(sys.prefix)/'Lib/site-packages';env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R)
code='import sys,runpy,importlib.util,pathlib;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core")is None;runpy.run_path('+repr(str(T/'reader.py'))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,check=True,timeout=120)
a=json.loads((D/'reader-result.json').read_bytes());b=json.loads((T/'reader-result.json').read_bytes());assert{k:v for k,v in a.items()if k!='seconds'}=={k:v for k,v in b.items()if k!='seconds'}
out=dict(status='PASS_PINNED_SOURCE_NATIVE_TRACE_BOUNDS',seconds=time.perf_counter()-start,dependencies=[dict(archive=n,sha256=sha,prefix=p)for n,sha,p in deps],native_absent=True,python_S_extracted_origins=True,new_Native_queries=0,new_games=0,new_training=0,real_primary_stops=True,regenerated_outputs=1,scope='Separateafter78payloadcapsule supplement: all1506Native trace integerbounds/features matchedCorecontexts; nonruntime readerregeneratedonly, no Native/timing/learning/AUXexecution orall-domainhistoryproof.')
tmp=D/'qualification.tmp';tmp.write_bytes((json.dumps(out,indent=2)+'\n').encode());os.replace(tmp,D/'qualification.json');print('TRACE_SOURCE_PASS',out['seconds'])
