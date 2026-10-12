import json,time,hashlib,sys
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task253';sys.path.insert(0,str(O));from codec import encode,decode,canonical
D=json.loads((O/'declaration.json').read_bytes());P=R/D['source'];assert hashlib.sha256(P.read_bytes()).hexdigest()==D['source_sha256'];assert not (O/'result.json').exists();started=time.monotonic();t=time.monotonic();X=json.loads(P.read_bytes());load_seconds=time.monotonic()-t;stats={'arrays':0,'elements':0};t=time.monotonic();Y=encode(X,stats);encode_seconds=time.monotonic()-t;t=time.monotonic();original_sha=hashlib.sha256(canonical(X)).hexdigest();decoded=decode(Y);assert hashlib.sha256(canonical(decoded)).hexdigest()==original_sha;assert decoded==X;verify_seconds=time.monotonic()-t;del decoded;metrics=[]
for i,n in enumerate((16,64,128)):
 xx=dict(X,calls=X['calls'][:n]);yy=dict(Y,calls=Y['calls'][:n]);arms={}
 for label,obj in ([('dense',xx),('compact',yy)] if i%2==0 else [('compact',yy),('dense',xx)]):
  cpu=time.process_time();wall=time.monotonic();serialized=json.dumps(obj,indent=2,allow_nan=False);arms[label]=dict(bytes=len(serialized.encode('utf-8')),seconds=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu);del serialized
 metrics.append(dict(frontier_calls=n,arms=arms))
(O/'compact_236.json').write_text(json.dumps(Y,indent=2,allow_nan=False),encoding='utf-8');out=dict(complete=True,source_bytes=D['source_bytes'],compact_bytes=(O/'compact_236.json').stat().st_size,source_file_sha256=D['source_sha256'],canonical_semantic_sha256=original_sha,roundtrip_complete_equal=True,stats=stats,load_seconds=load_seconds,encode_seconds=encode_seconds,verify_seconds=verify_seconds,metrics=metrics,total_seconds=time.monotonic()-started,scope=D['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
