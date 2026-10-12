import json,hashlib,zipfile,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';archive=O/'ACTUAL_MATURE_20261012_25.zip';manifest=O/'ACTUAL_MATURE_20261012_25_manifest.json'
assert not archive.exists() and not manifest.exists();private=set(json.loads((O/'task383/public_build_summary.json').read_text(encoding='utf-8'))['privacy_excluded_paths'])
paths=sorted(p for n in range(357,384) for p in (O/f'task{n:03d}').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp','.ini') and p.relative_to(R).as_posix() not in private)
rows=[];start=time.monotonic()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths:
  relative=p.relative_to(R).as_posix();data=p.read_bytes();z.writestr(relative,data);rows.append(dict(path=relative,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
with zipfile.ZipFile(archive) as z:
 assert set(z.namelist())=={r['path'] for r in rows}
 for row in rows:
  data=z.read(row['path']);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
out=dict(complete=True,archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=len(rows),raw_bytes=sum(r['bytes'] for r in rows),seconds=time.monotonic()-start,files=rows,archive_only_paths=[r['path'] for r in rows if r['bytes']>100000 or r['path'] in {'results/dev_aux/task362/see_replacement.txt','results/dev_aux/task374/candidate_see.inc','results/dev_aux/task374/usi_hook.inc'}],private_excluded_paths=sorted(private),excluded='No.local_agent, binaries/toolchain/sourcezip, rawSlack/stop/account/privateinputs; onlynewAgentgeneratedscience357..383. DerivedINIconfigs excluded.374source hashes+Agentpatch resources, thirdparty complete sources private; no rawaccount/Slackmetadata. Originals neverdeleted.')
manifest.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','members','raw_bytes','archive_bytes','archive_sha256','seconds')}))