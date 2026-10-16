from pathlib import Path
import subprocess,sys,json,time,collections
B=Path(sys.argv[1]).resolve();start=time.perf_counter();counts=collections.Counter();components={}
for script,result in [('consumer_base.py','base-consumer-result.json'),('consumer_compact.py','compact-consumer-result.json')]:
 r=subprocess.run([sys.executable,'-S',str(B/script),str(B)],capture_output=True,timeout=180);assert r.returncode==0,(r.stdout,r.stderr)
 d=json.loads((B/result).read_bytes());assert d['complete'];components[script]=d;counts.update(d['counts'])
out=dict(complete=True,counts=dict(counts),components=components,seconds=time.perf_counter()-start,scope='Actualfreshwholebase+compactsource-boundsearchdisabledpass; no newresearchquery/game/fit, sharedCore/compiler/host.')
(B/'source-consumer-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out),flush=True)
