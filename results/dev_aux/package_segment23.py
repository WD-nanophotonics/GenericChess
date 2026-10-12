import json,hashlib,zipfile,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';archive=O/'ACTUAL_MATURE_20261012_23.zip';manifest=O/'ACTUAL_MATURE_20261012_23_manifest.json'
assert not archive.exists() and not manifest.exists();private={'results/dev_aux/task316/audit.json'}
paths=sorted(p for n in range(313,332) for p in (O/f'task{n:03d}').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp','.ini') and p.relative_to(R).as_posix() not in private)
rows=[];start=time.monotonic()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths:
  relative=p.relative_to(R).as_posix();data=p.read_bytes();z.writestr(relative,data);rows.append(dict(path=relative,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
with zipfile.ZipFile(archive) as z:
 assert set(z.namelist())=={r['path'] for r in rows}
 for row in rows:
  data=z.read(row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
out=dict(complete=True,archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=len(rows),raw_bytes=sum(r['bytes'] for r in rows),seconds=time.monotonic()-start,files=rows,archive_only_paths=[r['path'] for r in rows if r['bytes']>100000],private_excluded_paths=sorted(private),excluded='No.local_agent, binaries/toolchain/sourcezip, rawSlack/stop/account/privateinputs; onlynewAgentgeneratedscience313..331. DerivedINIconfigs excluded.316rawoptioncommandswithlocalpaths private; public_audit.json explicitprojection andrawSHA retainsactualpriceack/eval/source evidence. Originals neverdeleted.')
manifest.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','members','raw_bytes','archive_bytes','archive_sha256','seconds')}))