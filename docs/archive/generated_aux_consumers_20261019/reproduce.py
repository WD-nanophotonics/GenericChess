"""Regenerate eleven receipt outputs with captured Python sources; no Native."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();A=Path(__file__).resolve().parent;P=R/'docs/archive/root_window_q4_service_20261019';start=time.perf_counter();deadline=start+300
m=json.loads((A/'manifest.json').read_bytes());old=json.loads((P/'manifest.json').read_bytes())
assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256']
assert hashlib.sha256((P/'evidence.zip').read_bytes()).hexdigest()==m['reused_product_source_archive_sha256']==old['archive_sha256']
X=R/'.local_agent'/('generated-aux-proof-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';T=X/'data'
def extract(archive,entries,dest,source_only=False):
 with zipfile.ZipFile(archive)as z:
  for name,record in entries.items():
   if source_only and not name.startswith('source/'):continue
   target=(dest/name).resolve();assert target.is_relative_to(dest.resolve());b=z.read(name);assert len(b)==record['bytes']and hashlib.sha256(b).hexdigest()==record['sha256'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
extract(P/'evidence.zip',old['files'],X,True);extract(A/'evidence.zip',m['files'],T)
for name in m['files']:
 if name.startswith('source_overlay/'):
  relative=name.removeprefix('source_overlay/');target=S/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((T/name).read_bytes())
jobs=[
('generated-aux-consumer-20261019','analyze.py','analysis.json'),
('generated-aux-consumer-20261019','policy-alias.py','policy-alias-result.json'),
('generated-aux-consumer-20261019','opening-preference.py','opening-preference-result.json'),
('generated-aux-consumer-20261019','legacy-filter-parity.py','legacy-filter-parity-result.json'),
('generated-aux-service-20261019','analyze.py','analysis.json'),
('generated-aux-service-20261019','reader.py','reader-result.json'),
('generated-aux-qpolicy-20261019','analyze.py','analysis.json'),
('generated-aux-qpolicy-20261019','reader.py','reader-result.json'),
('generated-aux-price-20261019','analyze.py','analysis.json'),
('generated-aux-price-20261019','reader.py','reader-result.json'),
('generated-aux-capture-20261019','analyze.py','analysis.json')]
def normalized(v):
 if isinstance(v,dict):return{k:normalized(w)for k,w in v.items()if k!='seconds'}
 if isinstance(v,list):return[normalized(w)for w in v]
 return v
site=Path(sys.prefix)/'Lib/site-packages';env=dict(os.environ);env.update(PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R),GC_PRODUCT_ARCHIVE_ROOT=str(P));results=[]
for directory,script,output in jobs:
 for n in ('rollout','advisor','slack'):
  flags=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(flags.get('stopped')or flags.get('user_paused'))
 q=T/directory;before=json.loads((q/output).read_bytes());env['GC_EXPERIMENT_ROOT']=str(q)
 driver="""import sys,importlib.util,runpy
from pathlib import Path
S=Path(SOURCE);sys.path[:0]=[str(S),SITE]
assert importlib.util.find_spec('generic_chess._native_core')is None
runpy.run_path(SCRIPT,run_name='__main__')
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
assert 'generic_chess._native_core'not in sys.modules
"""
 code='SOURCE='+repr(str(S))+';SITE='+repr(str(site))+';SCRIPT='+repr(str(q/script))+'\n'+driver
 tick=time.perf_counter();p=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,capture_output=True,text=True,encoding='utf8',timeout=max(.1,min(120,deadline-time.perf_counter())))
 (X/(directory+'-'+script+'.stdout')).write_text(p.stdout,encoding='utf8');(X/(directory+'-'+script+'.stderr')).write_text(p.stderr,encoding='utf8')
 if p.returncode:raise RuntimeError('Captured-source stage failed:'+directory+'/'+script+' '+p.stderr[-1200:])
 after=json.loads((q/output).read_bytes());assert normalized(before)==normalized(after),(directory,output)
 results.append(dict(directory=directory,script=script,output=output,seconds=time.perf_counter()-tick,numerical_and_semantic_fields_equal=True))
 print('SOURCE_RECEIPT_PASS',len(results),directory,script,flush=True)
out=dict(status='PASS_CAPTURED_SOURCE_ELEVEN_OUTPUTS',outputs=results,output_count=len(results),seconds=time.perf_counter()-start,technical_archive_sha256=m['archive_sha256'],product_source_archive_sha256=old['archive_sha256'],source_overlay_files=[x for x in m['files']if x.startswith('source_overlay/')],python_S=True,Native_absent=True,all_generic_modules_from_extracted_source=True,real_primary_stop_flags=True,no_faked_flags=True,new_Native_queries=0,new_games=0,new_training=0,old_UNKNOWN_references_rerun=0,scope='Receipt arithmetic and completeCore Session/PV/feature/pref reconstruction only. No newCoreq4 reference trees, Nativebuild orfitness rerun; originalnativechecked-edge receipts notindependentlyrerun here.')
# Qualification is a small technical publication copy; working directory remains private.
tmp=A/'qualification.tmp';tmp.write_bytes((json.dumps(out,indent=2)+'\n').encode());os.replace(tmp,A/'qualification.json')
private=dict(out,working_directory=str(X))
(X/'qualification.private.json').write_bytes((json.dumps(private,indent=2)+'\n').encode())
print('CAPTURED_SOURCE_COMPLETE',len(results),out['seconds'],flush=True)
