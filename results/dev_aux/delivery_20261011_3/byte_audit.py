"""Delivery byte audit; no engine imports, no fixture or timing replay."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
changes=git('diff','--cached','--name-only','-z').decode().split('\0')
paths=git('ls-files','-z').decode().split('\0')
paths=[p for p in paths if p]
scientific=[p for p in paths if any(p.startswith('results/dev_aux/task%03d/'%i) for i in range(27,43))]
assert scientific
rows=[]
for p in scientific:
 raw=(ROOT/p).read_bytes();staged=git('show',':'+p)
 rows.append(dict(path=p,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
  staged_sha256=hashlib.sha256(staged).hexdigest(),exact_bytes=raw==staged))
assert all(r['exact_bytes'] for r in rows),[r['path'] for r in rows if not r['exact_bytes']]
assert all(p=='.gitattributes' or p.startswith('results/dev_aux/') for p in changes if p),changes
logical=(ROOT/'results/dev_aux/task033/candidate_function.py').read_text(encoding='utf-8')
report=json.loads((ROOT/'results/dev_aux/task033/rank_merge.json').read_bytes())
assert hashlib.sha256(logical.encode()).hexdigest()==report['candidate_function_sha256']
out=dict(complete=True,scope='New staged task027-task042 scientific files; exact raw bytes, not normalized text.',
 scientific_files=len(rows),files=rows,
 logical_source_hash=dict(path='results/dev_aux/task033/candidate_function.py',
  field='candidate_function_sha256',meaning='LF logical generated string before Windows write_text',
  verified_normalized_read_text_sha256=hashlib.sha256(logical.encode()).hexdigest()),
 initial_failure=dict(at_utc='2026-10-11T06:29',affected_paths=23,
  cause='Git newline clean filtering; whitespace check alone passed; publication held',
  repair='Narrow task027-task042 -text attributes and restage; no historical result fields replaced'),
 limits='Manifest excludes itself and prose outside task directories. Private .local_agent records are not outgoing. This audit is delivery verification, not a scientific engine rerun.')
Path(__file__).with_name('byte_manifest.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('exact staged science bytes verified:',len(rows),'files; logical Task033 source hash separately verified')
