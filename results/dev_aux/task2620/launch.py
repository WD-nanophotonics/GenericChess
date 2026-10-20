"""One-shot task2620 launcher with actual PID and exit receipts."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'results/dev_aux/task2620/run-002'
def write(name,obj):
    with (RUN/name).open('x',encoding='utf-8') as f:f.write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def launch():
    if any((RUN/n).exists() for n in ('launch-claim.json','evaluation-started.json')): raise FileExistsError('no relaunch')
    plan=json.loads((RUN/'plan.json').read_text())
    for name,digest in plan['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest: raise ValueError('source changed: '+name)
    command=[sys.executable,'-m','results.dev_aux.task2620.evaluate']
    write('launch-claim.json',dict(command=command,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    start=time.perf_counter()
    with (RUN/'launcher.stdout').open('xb') as stdout,(RUN/'launcher.stderr').open('xb') as stderr:
        proc=subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr)
        write('launch-started.json',dict(pid=proc.pid,command=command,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        code=proc.wait()
    write('launch-exit.json',dict(return_code=code,wall_seconds=time.perf_counter()-start,
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return code
if __name__=='__main__': raise SystemExit(launch())
