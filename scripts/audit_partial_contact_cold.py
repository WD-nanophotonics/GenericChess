"""Three isolated arithmetic processes; no original construction rerun."""
from pathlib import Path
from time import monotonic, perf_counter
import hashlib
import json
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/partial_contact_cold_20261006.json'
SOURCES = ('scripts/audit_partial_contact_cold.py', 'scripts/partial_contact_prior.py',
           'docs/research/PARTIAL_CONTACT_COLD_PROTOCOL.md', 'scripts/research_record.py',
           'docs/research/data/diagnostic_duration_order_20261006.json')
CHILD = '''from time import perf_counter
start=perf_counter()
import hashlib,json
from pathlib import Path
from scripts.partial_contact_prior import PartialContactPrior
imports=perf_counter()-start
t=perf_counter()
r=json.loads(Path("docs/research/data/diagnostic_duration_order_20261006.json").read_text())
assert r["complete"] and r["source_hashes_unchanged"]
for p,digest in r["source_sha256"].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
load_hash=perf_counter()-t
t=perf_counter(); prior=PartialContactPrior(r["cumulative"],r["total"])
validate=perf_counter()-t
t=perf_counter(); value=prior.duration({"2":1}); difference=prior.difference({"H":1,"C":-1,"E":-1})
assert difference["strict_order_proved"] and value["normalized"]["R"]==(1,1)
arithmetic=perf_counter()-t
print(json.dumps(dict(import_seconds=imports,load_direct_hash_seconds=load_hash,constructor_seconds=validate,
                     arithmetic_seconds=arithmetic,whole_child_seconds=perf_counter()-start,
                     normalized_h=[str(v) for v in value["normalized"]["H"]])))
'''


def main():
    if OUT.exists(): raise FileExistsError('cold check never rerun')
    start = monotonic()
    r = dict(complete=False, rows=[], public_transitions=0, source_queries=0, geometry_queries=0,
             interpreter=sys.executable, command=['-X', 'utf8', '-c', CHILD],
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        for i in range(3):
            if monotonic()-start >= 15: raise TimeoutError('whole15sec cap')
            t = perf_counter()
            run = subprocess.run([sys.executable, '-X', 'utf8', '-c', CHILD], cwd=ROOT,
                                 capture_output=True, text=True, timeout=5)
            row = dict(index=i, external_seconds=perf_counter()-t, exit_code=run.returncode,
                       stdout=run.stdout, stderr=run.stderr); r['rows'].append(row)
            if run.returncode: raise ValueError('isolated child failed')
            row['measured'] = json.loads(run.stdout)
            row['startup_and_parent_overhead_seconds'] = row['external_seconds']-row['measured']['whole_child_seconds']
        if monotonic()-start >= 15: raise TimeoutError('whole15sec cap')
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'command')}))


if __name__ == '__main__': main()
