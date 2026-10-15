"""Validate the public archive and replay evidence with SEARCH DISABLED.
Use the unchanged public product source at the manifest source_base (or the
report delivery commit), its normal Native build and existing Python environment.
Does not rerun timings, generation, search, training or another Agent's work.
"""
from pathlib import Path
import sys,json,zipfile,hashlib,uuid,subprocess,time
R=Path.cwd();A=Path(__file__).resolve().parent;m=json.loads((A/'manifest.json').read_bytes());start=time.perf_counter()
assert hashlib.sha256((A/'evidence.zip').read_bytes()).hexdigest()==m['archive_sha256']
subprocess.run(['git','diff','--quiet',m['source_base'],'--','generic_chess','scripts'],check=True)
dest=R/'.local_agent'/('reserve-public-replay-'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True)
with zipfile.ZipFile(A/'evidence.zip')as z:
 assert z.testzip()is None
 assert set(z.namelist())=={x['member']for x in m['members']}
 for x in m['members']:
  blob=z.read(x['member']);assert len(blob)==x['bytes']and hashlib.sha256(blob).hexdigest()==x['public_sha256'];p=dest/x['member'];assert p.resolve().is_relative_to(dest.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
rows=[]
for label,args in [('cohorts',[str(dest/'research/consumer.py'),str(dest/'research'),str(R),str(dest/'inputs')]),('continuations',[str(dest/'research/continuation_replay.py'),str(dest/'research'),str(dest/'inputs')])]:
 r=subprocess.run([sys.executable]+args,cwd=R,capture_output=True,timeout=180);(dest/f'{label}.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(label,r.stdout.decode(errors='replace'),r.stderr.decode(errors='replace'));rows.append(dict(check=label,exit=r.returncode))
result=dict(complete=True,seconds=time.perf_counter()-start,archive_sha256=m['archive_sha256'],members=len(m['members']),rows=rows,cohorts=json.loads((dest/'research/consumer-replay.json').read_bytes()),continuations=json.loads((dest/'research/continuation-replay.json').read_bytes()),scope='Actual sanitized public-copy execution; product source unchanged, normal existing Native. Search/generation/training disabled, no timing or independent rule-engine claim.')
(dest/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
