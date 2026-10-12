import json,time,hashlib,importlib.util,math,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task308';sp=importlib.util.spec_from_file_location('sparse_codec',O/'codec.py');S=importlib.util.module_from_spec(sp);sp.loader.exec_module(S);start=time.monotonic();rows=[]
for task in (289,297,301):
 p=R/f'results/dev_aux/task{task}/result.json';original=json.loads(p.read_bytes());decoded=S.C.decode(original);encoded=S.encode(decoded);restored=S.decode(encoded);raw=S.canonical(decoded);assert raw==S.canonical(restored);q=O/f'compact_{task}.json';q.write_bytes(S.canonical(encoded));assert raw==S.canonical(S.decode(json.loads(q.read_bytes())));rows.append(dict(task=task,source_file_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),canonical_dense_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=p.stat().st_size,canonical_dense_bytes=len(raw),new_compact_bytes=q.stat().st_size,new_file_sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
# Independent JSON object_hook decoder recognizes both formats, distinct implementation.
def hook(d):
 if set(d)=={S.C.TAG}:z=d[S.C.TAG];return [z['value']]*z['count']
 if set(d)=={S.TAG}:
  z=d[S.TAG];out=[z['default']]*z['count']
  for i,v in z['entries']:out[i]=v
  return out
 return d
for z in rows:
 p=O/f"compact_{z['task']}.json";xx=json.loads(p.read_bytes(),object_hook=hook);assert hashlib.sha256(S.canonical(xx)).hexdigest()==z['canonical_dense_sha256']
# Observed plausible corruption risks: bool/int/float equality and negative zero.
probe=dict(counter_by_ply=[0]*70+[False,0.0,-0.0,1,1.0,True],legal_actions=['x']*76);rr=S.decode(S.encode(probe));assert S.canonical(rr)==S.canonical(probe);assert [type(v) for v in rr['counter_by_ply']]==[type(v) for v in probe['counter_by_ply']];assert math.copysign(1,rr['counter_by_ply'][72])==-1
out=dict(complete=True,files=rows,all_canonical_bytes_equal=True,independent_hook_decoder_verified=True,type_signedzero_fields_verified=True,seconds=time.monotonic()-start,scope='Onlycurrentresearchrecordstorage, observed297perquery33.4MB growingprefixrewrites427s motivatedrepair. AllactualNativefields retained; no arraylength/field/default/model/node change orrewritingfrozenrecords. Actualnewsizebytes notheap/RSS. No claimthisalonecaused427s ornewrun speedup; otherloadallowed.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))