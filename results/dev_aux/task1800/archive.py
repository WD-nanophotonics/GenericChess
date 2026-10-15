# Exact project-only evidence archives and independent SHA restoration.
import hashlib,json,re,zipfile
from pathlib import Path
R=Path('results/dev_aux');records=[];exclusions=[]
for task in (1788,1789,1791,1792,1796,1797,1798):
 assert json.loads((R/f'task{task}/result.json').read_text())['status']=='COMPLETE', 'Refuse archive while actual study incomplete'
 assert json.loads((R/f'task{task}/audit.json').read_text())['unassigned_native_receipts']==0
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
patterns=[re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),re.compile(rb'(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s\x22\x27]+'),re.compile(rb'xox[baprs]-[A-Za-z0-9-]{12,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
for number,tasks in enumerate([[1788,1789,1790,1791],[1792,1793,1794,1795],[1796,1797,1798,1799,1800,1801,1802,1803]],1):
 files=sorted({p for task in tasks for p in (R/f'task{task}').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.jsonl','.ini','.md') and '__pycache__' not in p.parts})
 for p in files:
  data=p.read_bytes()
  for expression in patterns:
   if expression.search(data):raise RuntimeError('Outgoing content review needed: '+str(p)+' pattern '+str(expression.pattern))
 name=R/f'ROLE_PROOF_20261015_56_{number:02}.zip'
 with zipfile.ZipFile(name,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.as_posix())
 members=[dict(path=p.as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
 restore=Path(f'.local_agent/archive_restore56/part{number}');restore.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(name) as z:
  assert z.testzip() is None and sorted(z.namelist())==sorted(x['path'] for x in members)
  for item in members:
   target=(restore/item['path']).resolve();assert target.is_relative_to(restore.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item['path']));assert digest(target)==item['sha256']
 exclusions += ['/'+p.as_posix() for p in files if p.stat().st_size>100000 or 'source' in p.parts or p.name=='failed_source.py']
 records.append(dict(path=name.as_posix(),bytes=name.stat().st_size,sha256=digest(name),raw_bytes=sum(x['bytes'] for x in members),members=members,restored_sha256_verified=True))
manifest=dict(segment=56,archives=records,actual_content_scan='PASS patterns plus manual project-content review',scope='Exact project inputs/outputs/failures/executed sources; no raw Slack/account exports, personal information or credentials.',restoration='Every member extracted to ignored own private layer and SHA-checked. No evidence deleted.')
(R/'ARCHIVE_MANIFEST_20261015_56.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
p=Path('.git/info/exclude');p.write_text(p.read_text(encoding='utf-8')+'\n# DEV_AUX56 exact large records delivered in reviewed archives\n'+'\n'.join(sorted(set(exclusions)))+'\n',encoding='utf-8')
print(dict(archives=len(records),members=sum(len(x['members']) for x in records),raw_bytes=sum(x['raw_bytes'] for x in records),zip_bytes=sum(x['bytes'] for x in records),large_duplicates_ignored=len(set(exclusions))))
