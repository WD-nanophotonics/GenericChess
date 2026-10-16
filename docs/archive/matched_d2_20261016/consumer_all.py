from pathlib import Path
import sys,json,subprocess,time,collections,hashlib
P=Path(sys.argv[1]).resolve();start=time.perf_counter();counts=collections.Counter();receipts=[]
for folder in[".","future-q1","future-depth6","cross-future","first-action-cause"]:
 b=P/folder;r=subprocess.run([sys.executable,"-S",str(b/"consumer.py"),str(b)],cwd=Path.cwd(),capture_output=True,timeout=300)
 assert r.returncode==0,(folder,r.stdout[-1000:],r.stderr[-2500:])
 d=json.loads((b/"consumer-result.json").read_bytes());assert d["complete"];counts.update(d["counts"]);receipts.append(dict(folder=folder,receipt=d,consumer_sha256=hashlib.sha256((b/"consumer.py").read_bytes()).hexdigest()))
r=subprocess.run([sys.executable,"-S",str(P/"consumer_extra.py"),str(P)],capture_output=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
d=json.loads((P/"consumer-extra-result.json").read_bytes());counts.update(d["counts"]);receipts.append(dict(folder="lateextra",receipt=d))
x=dict(complete=True,counts=dict(counts),stages=receipts,seconds=time.perf_counter()-start,scope="Oneactualfull sequentialsearchdisablednormalNative/Core state/history receiptpass. No newsearch/game/proof, samehost/compiler, oldclocks notauthenticated. Newexperimentalprivatecounts/timingnotrerun.")
(P/"consumer-all.json").write_bytes((json.dumps(x,indent=2)+"\n").encode());print(json.dumps(dict(complete=True,counts=x["counts"],seconds=x["seconds"])),flush=True)
