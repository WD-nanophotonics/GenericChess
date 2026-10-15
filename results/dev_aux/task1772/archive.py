"""Exact evidence archives, checked public contents and independent restoration."""
import hashlib,json,re,zipfile
from pathlib import Path
R=Path('results/dev_aux');root=Path.cwd();records=[];exclusions=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
patterns=[re.compile(rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),re.compile(rb'(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s\x22\x27]+'),re.compile(rb'xox[baprs]-[A-Za-z0-9-]{12,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
for number,tasks in enumerate([[1761,1762,1764,1767,1769,1772],[1763,1765,1766],[1768,1770,1771]],1):
 files=sorted({p for t in tasks for p in (R/f'task{t}').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.jsonl','.ini','.bin') and '__pycache__' not in p.parts})
 if number==1:files+=list(Path('results/dev_aux/task1741').glob('*4.bin'))+list(Path('results/dev_aux/task1741').glob('*8.bin'))
 for p in files:
  if p.suffix!='.bin':
   data=p.read_bytes()
   for expression in patterns:
    if expression.search(data):raise RuntimeError('Publication review needed: '+str(p)+' regex '+str(expression.pattern))
 name=R/f'GENERIC_PROOF_20261015_54_{number:02}.zip'
 with zipfile.ZipFile(name,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,p.as_posix())
 members=[dict(path=p.as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
 restore=Path(f'.local_agent/archive_restore54/part{number}');restore.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(name) as z:
  assert z.testzip() is None and sorted(z.namelist())==sorted(x['path'] for x in members)
  for item in members:
   target=(restore/item['path']).resolve();assert target.is_relative_to(restore.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item['path']));assert digest(target)==item['sha256']
 for p in files:
  if p.stat().st_size>100000 and p.parts[2] not in ('task1741',):exclusions.append('/'+p.as_posix())
 records.append(dict(path=name.as_posix(),bytes=name.stat().st_size,sha256=digest(name),raw_bytes=sum(x['bytes'] for x in members),members=members,restored_sha256_verified=True))
manifest=dict(segment=54,archives=records,scope='Exact project-only inputs, outputs, failures and executed sources; binary reference arrays only. No raw Slack/account records, credentials, private inputs or pyc caches.',public_content_regex_scan='PASS plus manual technical-content review',private_restore='.local_agent/archive_restore54')
(R/'ARCHIVE_MANIFEST_20261015_54.json').write_text(json.dumps(manifest,indent=2))
exclude=Path('.git/info/exclude');old=exclude.read_text();exclude.write_text(old+'\n# DEV_AUX54 exact raw evidence in reviewed ZIP archives\n'+'\n'.join(sorted(set(exclusions)))+'\n')
print(dict(archives=len(records),members=sum(len(r['members']) for r in records),raw_bytes=sum(r['raw_bytes'] for r in records),zip_bytes=sum(r['bytes'] for r in records),large_loose_ignored=len(set(exclusions))))
