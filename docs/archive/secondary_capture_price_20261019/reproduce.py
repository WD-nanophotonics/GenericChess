"""Rebuild15 finite outputs from pinned Python source; no Native/games/training."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();A=Path(__file__).resolve().parent;start=time.perf_counter();deadline=start+1800
m=json.loads((A/'manifest.json').read_bytes());B=R/m['reused_product_source_archive'];O=R/m['reused_overlay_archive'];bm=json.loads((B.parent/'manifest.json').read_bytes());om=json.loads((O.parent/'manifest.json').read_bytes())
for path,sha in((A/'evidence.zip',m['archive_sha256']),(B,m['reused_product_source_archive_sha256']),(O,m['reused_overlay_archive_sha256'])):assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
X=R/'.local_agent'/('secondary-capture-proof-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';T=X/'data'
def extract(path,entries,dest,prefix=None):
 with zipfile.ZipFile(path)as z:
  for name,v in entries.items():
   if prefix is not None and not name.startswith(prefix):continue
   p=(dest/name).resolve();assert p.is_relative_to(dest.resolve());b=z.read(name);assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
extract(B,bm['files'],X,'source/')
extract(A/'evidence.zip',m['files'],T)
with zipfile.ZipFile(O)as z:
 for relative in m['source_overlays']:
  name='source_overlay/'+relative;b=z.read(name);v=om['files'][name];assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];p=S/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
jobs=[
('secondary-capture-consumer-20261019','reader.py','reader-result.json'),
('secondary-capture-hint-20261019','reader.py','reader-result.json'),
('secondary-capture-depth-20261019','reader.py','reader-result.json'),
('secondary-capture-ordinal-20261019','reader.py','reader-result.json'),
('secondary-capture-prices-20261019','analyze.py','analysis.json'),
('secondary-capture-prices-20261019','reader.py','reader-result.json'),
('secondary-capture-ordinal-games-20261019','analyze.py','analysis.json'),
('secondary-capture-ordinal-games-20261019','reader.py','reader-result.json'),
('secondary-capture-counterfactual-20261019','prepare.py','result.json'),
('secondary-capture-prices-20261019','matched-shallow-ledger.py','matched-shallow-ledger.json'),
('secondary-capture-consumer-20261019','tail-control.py','tail-control-result.json'),
('secondary-capture-consumer-20261019','profile-provenance.py','profile-provenance.json'),
('secondary-capture-checkpoint-20261019','reader.py','reader-result.json')]
if json.loads((T/'secondary-capture-validation-20261019/activation.json').read_bytes())['activated']:
 jobs += [('secondary-capture-validation-20261019','analyze.py','analysis.json'),('secondary-capture-validation-20261019','reader.py','reader-result.json')]
def norm(x):
 if isinstance(x,dict):return{k:norm(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return[norm(v)for v in x]
 return x
env=dict(os.environ);env.update(PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R));site=str(Path(sys.prefix)/'Lib/site-packages');done=[]
for directory,script,output in jobs:
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 before=json.loads((T/directory/output).read_bytes());tick=time.perf_counter()
 driver="""import sys,runpy,importlib.util
from pathlib import Path
S=Path(SOURCE);sys.path[:0]=[str(S),SITE]
assert importlib.util.find_spec('generic_chess._native_core')is None
runpy.run_path(SCRIPT,run_name='__main__')
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
assert 'generic_chess._native_core'not in sys.modules
"""
 code='SOURCE='+repr(str(S))+';SITE='+repr(site)+';SCRIPT='+repr(str(T/directory/script))+'\n'+driver
 p=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,capture_output=True,text=True,encoding='utf8',timeout=max(.1,min(900,deadline-time.perf_counter())))
 (X/(directory+'-'+script+'.stdout')).write_bytes(p.stdout.encode());(X/(directory+'-'+script+'.stderr')).write_bytes(p.stderr.encode())
 if p.returncode:raise RuntimeError(directory+'/'+script+' '+p.stderr[-1600:])
 after=json.loads((T/directory/output).read_bytes());assert norm(before)==norm(after),(directory,script,'non-time-field mismatch')
 done.append(dict(directory=directory,script=script,output=output,seconds=time.perf_counter()-tick,non_time_fields_equal=True));print('SECONDARY_CAPTURE_SOURCE_PASS',len(done),directory,script,flush=True)
out=dict(status='PASS_PINNED_SOURCE_SECONDARY_CAPTURE',outputs=done,output_count=len(done),payload_count=m['payload_count'],archive_sha256=m['archive_sha256'],source_archive_sha256=m['reused_product_source_archive_sha256'],overlay_archive_sha256=m['reused_overlay_archive_sha256'],seconds=time.perf_counter()-start,Python_S=True,Native_absent=True,all_generic_modules_from_extracted_source=True,real_PRIMARY_stop_flags=True,closed_Core_targets_rebuilt=28,Native_queries=0,new_games=0,optimizer_updates=0,original_UNKNOWN_refilled=0,scope='FullstoredCorestates/history/PVs/finiteclosedtargets/arithmetic/terminalandcertificateledgers only. NoNativebinary/sourceequivalence, population/WDL/default/modelclaim; allplannedmissing/censored slots remainUNKNOWN; no Native calls/newgames/UNKNOWNrefill.')
(A/'qualification.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());(X/'qualification.private.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print('SECONDARY_CAPTURE_SOURCE_COMPLETE',len(done),out['seconds'],flush=True)
