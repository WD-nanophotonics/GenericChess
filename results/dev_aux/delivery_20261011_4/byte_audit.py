"""Exact new evidence index bytes; no semantic/numeric rerun."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];B=Path(__file__).parent
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
names=[p for p in git('ls-files','-z').decode().split('\0') if p]
paths=[p for p in names if any(p.startswith('results/dev_aux/task%03d/'%i) for i in range(43,55))]
assert paths
rows=[]
for p in paths:
 raw=(ROOT/p).read_bytes();indexed=git('show',':'+p)
 assert raw==indexed,p
 rows.append(dict(path=p,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),exact_index_bytes=True))
changes=[p for p in git('diff','--cached','--name-only','-z').decode().split('\0') if p]
allowed=lambda p:p=='.gitattributes' or p.startswith('results/dev_aux/') or p in ('AGENTS.md','docs/operations/COLLABORATION_LOG.md','docs/operations/DEV_AUX_WORKFLOW.md','docs/operations/AUXILIARY_VALIDATION.md')
assert all(allowed(p) for p in changes),changes
out=dict(complete=True,scope='New Task043-054 exact working/index bytes; outgoing scope includes auxiliary collaboration supplement',
 files=rows,scientific_files=len(rows),outgoing_paths=changes,
 limits='Does not establish execution correctness or remote delivery. Manifest excludes itself; dependency/source closure recorded separately. Private raw Slack/state not staged.')
(B/'byte_manifest.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('new exact index bytes verified',len(rows),'scientific files; allowed outgoing scope')
