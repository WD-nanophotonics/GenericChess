import json,hashlib,zipfile,time,re,ast
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';tag='20261013_31';whitelist=list(range(550,575));paths=sorted(p for n in whitelist for p in (O/f'task{n:03d}').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.tmp','.ini']);start=time.perf_counter();rows=[];archives=[];bins=[];current=[];size=0
patterns=[rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}',rb'U0C6[A-Z0-9]+',rb'T0C6[A-Z0-9]+',rb'C0C6[A-Z0-9]+',rb'(?i)(?:xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9]+|sk-proj-[A-Za-z0-9_-]+)',rb'C:[/\\]Users[/\\]wdai']
for p in paths:
 n=p.stat().st_size
 if current and size+n>128*1024**2:bins.append(current);current=[];size=0
 current.append(p);size+=n
if current:bins.append(current)
for i,ps in enumerate(bins,1):
 name=f'ACTUAL_MATURE_{tag}_{i:02}.zip';archive=O/name;assert not archive.exists()
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in ps:
   data=p.read_bytes();assert not any(re.search(pat,data) for pat in patterns),p.relative_to(R).as_posix();z.writestr(p.relative_to(R).as_posix(),data);rows.append(dict(path=p.relative_to(R).as_posix(),archive=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 assert archive.stat().st_size<95*1024**2;archives.append(dict(path=name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()));print(name,archive.stat().st_size,flush=True)
 for row in [r for r in rows if r['archive']==name]:
  with zipfile.ZipFile(archive) as z:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
out=dict(complete=True,tag=tag,archives=archives,files=rows,members=len(rows),raw_bytes=sum(r['bytes'] for r in rows),archive_bytes=sum(a['bytes'] for a in archives),seconds=time.perf_counter()-start,archive_only_paths=[r['path'] for r in rows if r['bytes']>100000],scope='Actualsegment31 nativecontroller/cap24pure/cap12mixed/ALLaudits/costs/coverage withALLnegativevalues andzero-queryfailedattempts;574INPUTSONLY no populationgo. Exactunique originals retained. No.local_agent/rawSlack/account/privateinput/toolchains/binaries/fullupstreamsource. 561duplicateszero-go retainedtransportprovenance notdoublecounted.')
(O/f'ACTUAL_MATURE_{tag}_manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ['members','raw_bytes','archive_bytes','seconds']}))
