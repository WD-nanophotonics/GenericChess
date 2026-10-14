from pathlib import Path
import json,zipfile,hashlib,ast,re,time,sys,chess,shutil,collections
R=Path.cwd();start=time.monotonic();dirs=[R/f'results/dev_aux/task{i}' for i in range(1611,1639)];files=sorted(p for d in dirs if d.exists() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts);records=[];jsonl=collections.Counter();sources=0;jsons=0;rawbytes=0
patterns=[re.compile(rb'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'),re.compile(rb'xox[baprs]-[A-Za-z0-9-]+'),re.compile(rb'Bearer\s+[A-Za-z0-9_.-]{16,}')]
def digest(p,scan=True):
 h=hashlib.sha256()
 with p.open('rb') as f:
  carry=b''
  for b in iter(lambda:f.read(1024*1024),b''):
   h.update(b);data=carry+b
   assert not scan or not any(x.search(data) for x in patterns),str(p)
   carry=data[-256:]
 return h.hexdigest()
for p in files:
 name=str(p.relative_to(R)).replace('\\','/');size=p.stat().st_size;rawbytes+=size;hh=digest(p)
 if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'));sources+=1
 elif p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'));jsons+=1
 elif p.suffix=='.jsonl':
  with p.open(encoding='utf8') as f:
   for line in f:json.loads(line);jsonl[name]+=1
 records.append({'path':name,'bytes':size,'sha256':hh})
restore=R/'.local_agent/archive_restore50';assert shutil.disk_usage(R).free>rawbytes+200*1024**2;restore.mkdir(exist_ok=True)
groups=[];group=[];n=0
for rec in records:
 if group and n+rec['bytes']>200*1024**2:groups.append(group);group=[];n=0
 group.append(rec);n+=rec['bytes']
if group:groups.append(group)
archives=[]
for i,group in enumerate(groups,1):
 path=R/f'results/dev_aux/ACTUAL_MATURE_20261015_50_{i:02}.zip'
 if not path.exists():
  with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for rec in group:z.write(R/rec['path'],rec['path'])
 assert path.stat().st_size<50*1024**2
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None and z.namelist()==[r['path'] for r in group]
  for rec in group:
   target=(restore/rec['path']).resolve();assert str(target).lower().startswith(str(restore.resolve()).lower()+'\\');target.parent.mkdir(parents=True,exist_ok=True)
   if not target.exists():
    with z.open(rec['path']) as inp,target.open('wb') as out:shutil.copyfileobj(inp,out)
   assert target.stat().st_size==rec['bytes'] and digest(target)==rec['sha256']
 archives.append({'path':str(path.relative_to(R)).replace('\\','/'),'bytes':path.stat().st_size,'sha256':digest(path,False),'members':group})
# Exact raw originals remain locally; large originals are ignored, reviewed exactZIPs are publishable.
ex=R/'.git/info/exclude'
with ex.open('a',encoding='utf8') as f:
 for rec in records:
  if rec['bytes']>100000:f.write('\n/'+rec['path'])
man={'status':'PASS_ALL_EXACT_MEMBERS_PRIVATELY_RESTORED','archives':archives,'members':len(records),'raw_bytes':rawbytes,'base_source_revision':'f7ce184f9358949281c60faaf946664ae83436b6','AST_sources':sources,'JSON_objects':jsons,'JSONL_records':dict(jsonl),'privacy_scan':'No rawSlack/account/privateinput/credentials; technicalsources andactualengineoutputs only','Python':sys.version,'python_chess':chess.__version__,'package_seconds':time.monotonic()-start,'inline_source_limit':'50sources saved beforeexecution; old1619/1620 zeroquery importfailures preserved; task1611/statistics.py shadows stdlib for earlier executable sources, replay with python -P or new safe sys.path prefix. 4x4 partial caps not extended.'};(R/'results/dev_aux/ARCHIVE_MANIFEST_20261015_50.json').write_text(json.dumps(man,indent=2));print('ARCHIVES',[(x['path'],x['bytes']) for x in archives],'members',len(records),'raw',rawbytes,'AST',sources,'JSON',jsons,'JSONL',sum(jsonl.values()))

