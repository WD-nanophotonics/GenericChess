"""Exact closed science evidence, no private account records or executables."""
from pathlib import Path
import json,hashlib,zipfile,re
OUT=Path('results/dev_aux');files={}
for task in range(1861,1883):
 for p in (OUT/f'task{task}').rglob('*'):
  if p.is_file() and p.suffix in ('.py','.json','.jsonl','.ini','.md') and '__pycache__' not in p.parts:files[p.as_posix()]=p.read_bytes()
for name in ['results/dev_aux/task1846/rules.json','results/dev_aux/task1846/qualification.json','results/dev_aux/task1848/games.jsonl','results/dev_aux/task1848/moves.jsonl','results/dev_aux/task1857/result.json','results/dev_aux/task1860/verification_timeout_case.json','results/dev_aux/task1869/audit_report-corrected.json','results/dev_aux/task1877/audit_corrected.json','results/dev_aux/QA_20261015_61.json','results/dev_aux/COST_20261015_61.json','results/dev_aux/FAILURES_20261015_61.json']:
 files[name]=Path(name).read_bytes()
markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text())
for name,data in files.items():
 assert not name.startswith('.local_agent/') and '..' not in Path(name).parts
 assert all(v.encode() not in data for m in markers for v in (m,m.replace('\\','/'),json.dumps(m)[1:-1])),name
 assert not re.search(rb'(?:xox[baprs]-[A-Za-z0-9-]{15,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',data),name
members={n:dict(bytes=len(d),sha256=hashlib.sha256(d).hexdigest()) for n,d in sorted(files.items())}
manifest=dict(status='EXACT_CLOSED_EVIDENCE_PLUS_FROZEN_UNRUN_NEXT_PLAN',files=members,scope='All61closedsourcevariants/plans/results/fullactualpolicy/Native/input/reference/failures;1881next192gameplan isNOTEXECUTED. Currentruntime/tests sourceZIP381 plus this evidence includes everylateproducer/auditor, notfreshNativegame rerun. QAsealedbeforeactualsessionfinish; finaldirectGitQA/report carries acceptedendtime. Oldpolicy/partialcaps unchanged.')
p=OUT/'EVIDENCE_20261015_61.zip'
with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for name,data in sorted(files.items()):z.writestr(name,data)
 z.writestr('MANIFEST61EVIDENCE.json',json.dumps(manifest,indent=2).encode())
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 for n,row in members.items():assert hashlib.sha256(z.read(n)).hexdigest()==row['sha256']
archives=[]
for name in ['SOURCE_REPRO_20261015_61.zip','SOURCE_REPRO_FINAL_20261015_61.zip','EVIDENCE_20261015_61.zip']:
 f=OUT/name;archives.append(dict(path=name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
result=dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=archives,evidence_files=len(files),evidence_raw_bytes=sum(map(len,files.values())),private_layer_excluded=True,current_source_files=381,working_tests=298,independent_restored_tests=298,scope=manifest['scope'])
with (OUT/'ARCHIVE_MANIFEST_20261015_61.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
