"""Rebuild nine finite outputs from pinned Python source; no Native or games."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();A=Path(__file__).resolve().parent;P=R/'docs/archive/root_window_q4_service_20261019';start=time.perf_counter();deadline=start+300
m=json.loads((A/'manifest.json').read_bytes());old=json.loads((P/'manifest.json').read_bytes());assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256'];assert hashlib.sha256((P/'evidence.zip').read_bytes()).hexdigest()==m['reused_product_source_archive_sha256']==old['archive_sha256']
X=R/'.local_agent'/('compound-proof-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';T=X/'data'
def extract(path,entries,dest,source_only=False):
 with zipfile.ZipFile(path)as z:
  for name,receipt in entries.items():
   if source_only and not name.startswith('source/'):continue
   p=(dest/name).resolve();assert p.is_relative_to(dest.resolve());b=z.read(name);assert len(b)==receipt['bytes']and hashlib.sha256(b).hexdigest()==receipt['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
extract(P/'evidence.zip',old['files'],X,True);extract(A/'evidence.zip',m['files'],T)
for name in m['files']:
 if name.startswith('source_overlay/'):
  target=S/name.removeprefix('source_overlay/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((T/name).read_bytes())
jobs=[
('compound-consumer-20261019','verify-controls.py','controls-reader-result.json'),
('compound-consumer-20261019','verify-inputs.py','input-reader-result.json'),
('compound-window-20261019','analyze.py','analysis.json'),
('compound-window-20261019','reader.py','reader-result.json'),
('compound-window-20261019','mechanism-audit.py','mechanism-audit.json'),
('compound-alias-hint-20261019','analyze.py','analysis.json'),
('compound-root-prior-20261019','analyze.py','analysis.json'),
('compound-filter-placement-20261019','reader.py','result.json'),
('compound-filter-placement-20261019','witness.py','witness.json')]
def norm(v):
 if isinstance(v,dict):return{k:norm(x)for k,x in v.items()if k!='seconds'}
 if isinstance(v,list):return[norm(x)for x in v]
 return v
env=dict(os.environ);env.update(PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R));site=Path(sys.prefix)/'Lib/site-packages';outputs=[]
for directory,script,output in jobs:
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 q=T/directory;before=json.loads((q/output).read_bytes())
 driver="""import sys,runpy,importlib.util
from pathlib import Path
S=Path(SOURCE);sys.path[:0]=[str(S),SITE]
assert importlib.util.find_spec('generic_chess._native_core')is None
runpy.run_path(SCRIPT,run_name='__main__')
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
assert 'generic_chess._native_core'not in sys.modules
"""
 code='SOURCE='+repr(str(S))+';SITE='+repr(str(site))+';SCRIPT='+repr(str(q/script))+'\n'+driver
 tick=time.perf_counter();p=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,capture_output=True,text=True,encoding='utf8',timeout=max(.1,min(180,deadline-time.perf_counter())));(X/(directory+'-'+script+'.stdout')).write_text(p.stdout,encoding='utf8');(X/(directory+'-'+script+'.stderr')).write_text(p.stderr,encoding='utf8')
 if p.returncode:raise RuntimeError(directory+'/'+script+' '+p.stderr[-1800:])
 after=json.loads((q/output).read_bytes());assert norm(before)==norm(after),(directory,output)
 outputs.append(dict(directory=directory,script=script,output=output,seconds=time.perf_counter()-tick,numerical_and_semantic_fields_equal=True));print('COMPOUND_SOURCE_PASS',len(outputs),directory,script,flush=True)
out=dict(status='PASS_CAPTURED_SOURCE_NINE_OUTPUTS',outputs=outputs,output_count=len(outputs),seconds=time.perf_counter()-start,technical_payloads=m['payload_count'],technical_archive_sha256=m['archive_sha256'],product_source_archive_sha256=old['archive_sha256'],source_overlays=m['source_overlays'],Python_S=True,Native_absent=True,all_generic_modules_from_extracted_source=True,real_PRIMARY_stop_flags=True,completed_Core_targets_rebuilt=86,original_UNKNOWN_references_rerun=0,Native_searches=0,Native_policy_calls=0,new_games=0,optimizer_updates=0,scope='Receipt arithmetic/fullCoreSession/PVs/completepolicyinputs/savedmodels/closedreferences/existingfeatures/filterwitness only. NoNativebinary/sourceequivalence, game/train rerun orwhole-domain/utilityclaim.')
(A/'qualification.json').write_bytes((json.dumps(out,indent=2)+'\n').encode('utf8'));(X/'qualification.private.json').write_text(json.dumps(dict(out,working_directory=str(X)),indent=2)+'\n',encoding='utf8');print('COMPOUND_SOURCE_COMPLETE',len(outputs),out['seconds'],flush=True)
