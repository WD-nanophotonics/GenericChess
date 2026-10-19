"""Pinned Core/Python source; retained Native receipts only, never rerun Native/TRAIN."""
from pathlib import Path
import sys,os,json,zipfile,hashlib,subprocess,time,uuid
R=Path.cwd();A=Path(__file__).resolve().parent;start=time.perf_counter();m=json.loads((A/'manifest.json').read_bytes());X=R/'.local_agent'/('td-service-proof-'+uuid.uuid4().hex[:10]);X.mkdir();S=X/'source';T=X/'data'
def archive(key):
 p=R/m[key];assert hashlib.sha256(p.read_bytes()).hexdigest()==m[key+'_sha256'];return p,json.loads((p.parent/'manifest.json').read_bytes())
def extract(p,entries,dest,selected=None):
 with zipfile.ZipFile(p)as z:
  for name,v in entries.items():
   if selected is not None and name not in selected:continue
   out=(dest/name).resolve();assert out.is_relative_to(dest.resolve());b=z.read(name);assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
B,b=archive('reused_product_source_archive');O,o=archive('reused_overlay_archive');P,p=archive('reused_evidence_archive');assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256'];extract(B,b['files'],X,{n for n in b['files']if n.startswith('source/')});extract(A/'evidence.zip',m['files'],T);extract(P,p['files'],T,set(m['reused_evidence_members']))
with zipfile.ZipFile(O)as z:
 for rel in m['source_overlays']:
  name='source_overlay/'+rel;v=o['files'][name];data=z.read(name);assert len(data)==v['bytes']and hashlib.sha256(data).hexdigest()==v['sha256'];out=S/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
D=T/'td-query-contract-20261019';site=str(Path(sys.prefix)/'Lib/site-packages');env=dict(os.environ,PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R));jobs=[('reader.py','reader-result.json',False),('source_query.py','source-single-result.json',False),('post-return-control.py','post-return-before.json',True),('post-return-control.py','post-return-after.json',False)];done=[]
def norm(x):
 if isinstance(x,dict):return{k:norm(v)for k,v in x.items()if k not in('seconds','actual_query_seconds')}
 if isinstance(x,list):return[norm(v)for v in x]
 return x
for script,output,before_adapter in jobs:
 for n in('rollout','advisor','slack'):
  flags=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(flags.get('stopped')or flags.get('user_paused'))
 expected=json.loads((D/output).read_bytes());tick=time.perf_counter()
 code='SOURCE='+repr(str(S))+';DATA='+repr(str(D))+';SITE='+repr(site)+';SCRIPT='+repr(script)+';OUTPUT='+repr(output)+';BEFORE='+repr(before_adapter)+'\n'+"""import sys,runpy,importlib.util
from pathlib import Path
S=Path(SOURCE);D=Path(DATA);sys.path[:0]=[str(D),str(S),SITE]
assert importlib.util.find_spec('generic_chess._native_core')is None
if BEFORE:
 spec=importlib.util.spec_from_file_location('native_receipt',D/'native_receipt-before.py');adapter=importlib.util.module_from_spec(spec);sys.modules['native_receipt']=adapter;spec.loader.exec_module(adapter)
sys.argv=[str(D/SCRIPT),OUTPUT];runpy.run_path(str(D/SCRIPT),run_name='__main__')
assert all(Path(v.__file__).resolve().is_relative_to(S)for k,v in sys.modules.items()if k.startswith('generic_chess')and getattr(v,'__file__',None))
assert all(Path(v.__file__).resolve().is_relative_to(D/'dependency-source')for k,v in sys.modules.items()if k.startswith('results.dev_aux.')and getattr(v,'__file__',None))
assert 'generic_chess._native_core'not in sys.modules
"""
 proc=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,capture_output=True,text=True,encoding='utf8',timeout=min(120,max(.1,300-(time.perf_counter()-start))));(X/(output+'.stdout')).write_bytes(proc.stdout.encode());(X/(output+'.stderr')).write_bytes(proc.stderr.encode())
 if proc.returncode:raise RuntimeError(script+' '+proc.stderr[-2000:])
 actual=json.loads((D/output).read_bytes());assert norm(expected)==norm(actual),(script,output);done.append(dict(script=script,output=output,before_adapter=before_adapter,seconds=time.perf_counter()-tick,non_time_fields_equal=True));print('TD_CAPTURED_SOURCE_PASS',output,flush=True)
q=dict(status='PASS_PINNED_CORE_SOURCE_FOUR_OUTPUTS',jobs=done,output_count=4,payload_count=m['payload_count'],archive_sha256=m['archive_sha256'],Python_S=True,Native_absent=True,generic_module_origin_checked=True,published_source_query_module_origin_checked=True,actual_source_query_calls=1,Native_queries=0,TRAIN_EVAL_games=0,optimizer_updates=0,original_UNKNOWN_refilled=0,seconds=time.perf_counter()-start,scope='Replays648 recordedNative PVs/1284edges with capturedCore; evaluates existing closed D3 trees atD2, exactreceipt arithmetic/wholedeadline accounting; executes ONE alreadyclosed publishedquery overcapturedPRIMARYCore, not originalAUXCore. Bothresearchadapterfaultinjection versions reproduced, no newNative/library migration/learner execution.')
(A/'qualification.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print('TD_CAPTURED_SOURCE_COMPLETE',q['seconds'],flush=True)
