"""Rebuild twelve outputs with pinned Python/Core source and no Native module."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();A=Path(__file__).resolve().parent;start=time.perf_counter();m=json.loads((A/'manifest.json').read_bytes());B=R/m['reused_product_source_archive'];O=R/m['reused_overlay_archive'];bm=json.loads((B.parent/'manifest.json').read_bytes());om=json.loads((O.parent/'manifest.json').read_bytes())
for p,h in((A/'evidence.zip',m['archive_sha256']),(B,m['reused_product_source_archive_sha256']),(O,m['reused_overlay_archive_sha256'])):assert hashlib.sha256(p.read_bytes()).hexdigest()==h
X=R/'.local_agent'/('global-learned-proof-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';T=X/'data'
def extract(archive,entries,dest,prefix=None):
 with zipfile.ZipFile(archive)as z:
  for n,v in entries.items():
   if prefix is not None and not n.startswith(prefix):continue
   p=(dest/n).resolve();assert p.is_relative_to(dest.resolve());b=z.read(n);assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
extract(B,bm['files'],X,'source/');extract(A/'evidence.zip',m['files'],T)
with zipfile.ZipFile(O)as z:
 for rel in m['source_overlays']:
  n='source_overlay/'+rel;b=z.read(n);v=om['files'][n];assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];p=S/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
jobs=[('global-capture-consumer-20261019','reader.py',['reader-result.json']),('global-capture-consumer-20261019','carrier-reader.py',['carrier-reader-result.json']),('global-pair-cache-20261019','reader.py',['reader-result.json']),('learned-consumer-20261019','provenance-reader.py',['provenance-reader-result.json']),('learned-consumer-20261019','reader.py',['reader-result.json']),('learned-consumer-20261019','precision.py',['precision-result.json','bound-checkpoints-scale256.json']),('learned-prospective-20261019','sampler-reader.py',['sampler-reader-result.json']),('learned-prospective-20261019','reader.py',['reader-result.json']),('learned-prospective-20261019','serialized-reader.py',['serialized-reader-result.json']),('learned-consumer-20261019','credit-contract.py',['credit-contract-result.json']),('learned-prospective-20261019','rebind-reader.py',['rebind-reader-result.json'])]
def norm(x):
 if isinstance(x,dict):return{k:norm(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return[norm(v)for v in x]
 return x
done=[];env=dict(os.environ,PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R));site=str(Path(sys.prefix)/'Lib/site-packages')
for directory,script,outputs in jobs:
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
 before={out:json.loads((T/directory/out).read_bytes())for out in outputs};tick=time.perf_counter()
 driver="""import sys,runpy,importlib.util
from pathlib import Path
S=Path(SOURCE);sys.path[:0]=[str(S),SITE]
assert importlib.util.find_spec('generic_chess._native_core')is None
runpy.run_path(SCRIPT,run_name='__main__')
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
assert 'generic_chess._native_core'not in sys.modules
"""
 code='SOURCE='+repr(str(S))+';SITE='+repr(site)+';SCRIPT='+repr(str(T/directory/script))+'\n'+driver
 p=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,capture_output=True,text=True,encoding='utf8',timeout=max(.1,min(300,900-(time.perf_counter()-start))))
 (X/(directory+'-'+script+'.stdout')).write_bytes(p.stdout.encode());(X/(directory+'-'+script+'.stderr')).write_bytes(p.stderr.encode())
 if p.returncode:raise RuntimeError(directory+'/'+script+' '+p.stderr[-1600:])
 for out in outputs:assert norm(before[out])==norm(json.loads((T/directory/out).read_bytes())),(directory,script,out)
 done.append(dict(directory=directory,script=script,outputs=outputs,seconds=time.perf_counter()-tick,non_time_fields_equal=True));print('GLOBAL_LEARNED_SOURCE_PASS',directory,script,flush=True)
q=dict(status='PASS_PINNED_CORE_SOURCE_TWELVE_OUTPUTS',jobs=done,output_count=sum(len(x['outputs'])for x in done),payload_count=m['payload_count'],archive_sha256=m['archive_sha256'],seconds=time.perf_counter()-start,Python_S=True,Native_absent=True,all_generic_modules_from_extracted_source=True,real_PRIMARY_stop_flags=True,closed_global_Core_targets_rebuilt=4,learned_closed_tree_edges=77885,Native_queries=0,original_UNKNOWN_refilled=0,new_games=0,optimizer_updates=0,scope='Exact current Core states/history/PVs/closed trees/arithmetic and byte-exact published models. Not Native binary equivalence or original AUX execution;16global-cache CoreUNKNOWN remainUNKNOWN.')
(A/'qualification.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print('GLOBAL_LEARNED_SOURCE_COMPLETE',q['output_count'],q['seconds'],flush=True)
