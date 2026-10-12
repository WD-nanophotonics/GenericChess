import json,time,hashlib,sys
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task255';O.mkdir(exist_ok=True);sys.path.insert(0,str(R/'results/dev_aux/task253'));from codec import encode,decode,canonical
P=R/'results/dev_aux/task252/result.json';X=json.loads(P.read_bytes());assert X['complete'];calls=[c for c in X['calls'] if c['arm']=='replay'];assert len(calls)==16;import importlib.util
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P166=importlib.util.module_from_spec(s);s.loader.exec_module(P166);d=dict(task_id='255',question='Doobservedserialization savings also holdinactualownatomic progresswrite stage?',source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),frontiers=[4,8,16],conditions='Samefrozen16actualreplay-armrecords252, allNative/trajectory fieldsincluded, densevslosslessconstantcodec, oneactualatomicwrite eachfrontier/method counterbalancedorder. No newgames/searches. Everywrittenfile decodescanonicalhash identicaltofrontier.',scope='FileIOstage measurementnotengine speed orold236fullbatchcausalprofile. Originalrawsourcesunchanged; sparsewritefiles derivefromAgentdata, no uniqueevidencecleanup.');(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');rows=[];start=time.monotonic()
for i,n in enumerate(d['frontiers']):
 v=dict(complete=True,calls=calls[:n]);compact=encode(v);sha=hashlib.sha256(canonical(v)).hexdigest();arms={}
 for mode,obj in ([('dense',v),('compact',compact)] if i%2==0 else [('compact',compact),('dense',v)]):
  cpu=time.process_time();wall=time.monotonic();path=O/(mode+'_progress.json');P166.A.atomic_json(path,obj);duration=time.monotonic()-wall;cput=time.process_time()-cpu;read=json.loads(path.read_bytes());restored=decode(read) if mode=='compact' else read;assert hashlib.sha256(canonical(restored)).hexdigest()==sha;arms[mode]=dict(seconds=duration,cpu_seconds=cput,bytes=path.stat().st_size,canonical_roundtrip_sha256=sha)
 rows.append(dict(frontier=n,arms=arms))
out=dict(complete=True,seconds=time.monotonic()-start,rows=rows,scope=d['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
