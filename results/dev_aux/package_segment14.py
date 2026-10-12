"""Package only reviewed Agent-created experiment artifacts; no .local_agent/rawSlack/binaries."""
import hashlib,json,zipfile,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];BASE=R/'results/dev_aux';archive=BASE/'ACTUAL_MATURE_20261012_14.zip';manifest=BASE/'ACTUAL_MATURE_20261012_14_manifest.json';started=time.monotonic()
paths=[]
for n in range(120,133):
 for p in sorted((BASE/f'task{n}').rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp'):
   assert p.resolve().is_relative_to(R.resolve());assert p.suffix in ('.py','.json','.jsonl','.ini','.patch')
   paths.append(p)
rows=[]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths:
  raw=p.read_bytes();name=p.relative_to(R).as_posix();info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
  rows.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.namelist())==len(rows)
 for r in rows:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
large=[r['path'] for r in rows if r['bytes']>1_000_000]
p=R/'.gitignore';text=p.read_text(encoding='utf-8');text+='\n# Segment14 exact large scientific records are preserved in verified archive.\n'+'\n'.join('/'+n for n in large)+'\n';p.write_text(text,encoding='utf-8')
result=dict(archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(rows),uncompressed_bytes=sum(r['bytes'] for r in rows),all_member_bytes_verified=True,large_records_gitignored_but_archived=large,rows=rows,scope='Agent-created source/declarations/scientificdata only; excludes .local_agent/private/rawSlack/credentials/executables',wall_seconds=time.monotonic()-started)
manifest.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','large_records_gitignored_but_archived')}))