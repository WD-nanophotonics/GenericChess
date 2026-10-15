# Exact project-only evidence archives and independent SHA restoration.
import hashlib,json,re,zipfile
from pathlib import Path
R=Path('results/dev_aux');records=[];exclusions=[]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
patterns=[re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),re.compile(rb'(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s\x22\x27]+'),re.compile(rb'xox[baprs]-[A-Za-z0-9-]{12,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
for number,tasks in enumerate([[1773,1774,1775,1776,1777,1778],[1779,1780,1781,1782],[1783,1784,1785,1786,1787]],1):
 files=sorted({p for task in tasks for p in (R/f'task{task}').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.jsonl','.ini','.md') and '__pycache__' not in p.parts})
 for p in files:
  data=p.read_bytes()
  for expression in patterns:
   if expression.search(data):raise RuntimeError('Outgoing content review needed: '+str(p)+' pattern '+str(expression.pattern))
 name=R/f'PROOF_TAIL_20261015_55_{number:02}.zip'
 with zipfile.ZipFile(name,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.as_posix())
 members=[dict(path=p.as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
 restore=Path(f'.local_agent/archive_restore55/part{number}');restore.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(name) as z:
  assert z.testzip() is None and sorted(z.namelist())==sorted(x['path'] for x in members)
  for item in members:
   target=(restore/item['path']).resolve();assert target.is_relative_to(restore.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item['path']));assert digest(target)==item['sha256']
 exclusions += ['/'+p.as_posix() for p in files if p.stat().st_size>100000]
 records.append(dict(path=name.as_posix(),bytes=name.stat().st_size,sha256=digest(name),raw_bytes=sum(x['bytes'] for x in members),members=members,restored_sha256_verified=True))
manifest=dict(segment=55,archives=records,actual_content_scan='PASS patterns plus manual project-content review',scope='Exact project inputs/outputs/failures/executed sources; no raw Slack/account exports, personal information or credentials.',restoration='Every member extracted to ignored own private layer and SHA-checked. No evidence deleted.')
(R/'ARCHIVE_MANIFEST_20261015_55.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
p=Path('.git/info/exclude');p.write_text(p.read_text(encoding='utf-8')+'\n# DEV_AUX55 exact large records delivered in reviewed archives\n'+'\n'.join(sorted(set(exclusions)))+'\n',encoding='utf-8')
print(dict(archives=len(records),members=sum(len(x['members']) for x in records),raw_bytes=sum(x['raw_bytes'] for x in records),zip_bytes=sum(x['bytes'] for x in records),large_duplicates_ignored=len(set(exclusions))))
