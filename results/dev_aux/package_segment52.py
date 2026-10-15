from pathlib import Path
import json,ast,zipfile,hashlib,shutil,re,time,sys,collections
R=Path.cwd();D=R/'results/dev_aux';start=time.perf_counter();files=sorted(p for i in range(1671,1718) for p in (D/f'task{i}').rglob('*') if p.is_file() and '__pycache__' not in p.parts);records=[];syntax=[];counts=collections.Counter();patterns=[re.compile(rb'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'),re.compile(rb'xox[baprs]-[A-Za-z0-9-]+'),re.compile(rb'Bearer\s+[A-Za-z0-9_.-]{16,}')];expected_syntax={'results/dev_aux/task1701/root_strata.py','results/dev_aux/task1706/forecast.py'}
def sha(p):
 h=hashlib.sha256();carry=b''
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):
   h.update(b);s=carry+b;assert not any(x.search(s) for x in patterns),str(p);carry=s[-256:]
 return h.hexdigest()
for p in files:
 rel=p.relative_to(R).as_posix();rec={'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)}
 if p.suffix=='.py':
  try:ast.parse(p.read_text(encoding='utf-8-sig'));counts['AST_valid']+=1
  except SyntaxError as ex:assert rel in expected_syntax;syntax.append({'path':rel,'reason':str(ex),'role':'Originalfailedpreparedsource,preservedandseparatefixedsourceexecuted'});counts['AST_expected_failed']+=1
 elif p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'));counts['JSON']+=1
 elif p.suffix=='.jsonl':
  for line in p.open(encoding='utf8'):json.loads(line);counts['JSONL_rows']+=1
 records.append(rec)
assert {x['path'] for x in syntax}==expected_syntax;total=sum(x['bytes'] for x in records);free=shutil.disk_usage(R).free;assert free>total+200*1024**2;restore=R/'.local_agent/archive_restore52';restore.mkdir(exist_ok=True);groups=[];g=[];size=0
for rec in records:
 if g and size+rec['bytes']>180*1024**2:groups.append(g);g=[];size=0
 g.append(rec);size+=rec['bytes']
if g:groups.append(g)
archives=[]
for i,g in enumerate(groups,1):
 out=D/f'ACTUAL_MATURE_20261015_52_{i:02}.zip'
 with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for rec in g:z.write(R/rec['path'],rec['path'])
 assert out.stat().st_size<50*1024**2
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None and z.namelist()==[r['path'] for r in g]
  for rec in g:
   target=(restore/rec['path']).resolve();assert str(target).lower().startswith(str(restore.resolve()).lower()+'\\');target.parent.mkdir(parents=True,exist_ok=True)
   with z.open(rec['path']) as inp,target.open('wb') as dst:shutil.copyfileobj(inp,dst)
   assert target.stat().st_size==rec['bytes'] and sha(target)==rec['sha256']
 archives.append({'path':out.relative_to(R).as_posix(),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'members':g})
with (R/'.git/info/exclude').open('a',encoding='utf8') as f:
 for rec in records:
  if rec['bytes']>100000:f.write('\n/'+rec['path'])
manifest={'status':'PASS_ALL_TECHNICAL_MEMBERS_BYTE_EXACT_RESTORED_PRIVATELY','base_source_revision':'8ac8a9fc44354cc84ff5fbfe5e3361cb844be050','members':len(records),'raw_bytes':total,'free_bytes_before_restore':free,'archives':archives,'validation':dict(counts),'expected_preserved_AST_failures':syntax,'privacy':'Alltechnicalsources/generatedpositions/Nativeoutputs only; no rawSlack/account/userinput/credentials. Private rawSlack separatelyignored andnotincluded.','source_bytes':'Exactarchivebytesauthoritative, individualGittextmaynormalizeLF. Originalruntimeandpreparefailuresretained, newuniqueoutputsfixed; oldfrozenlimitsneverextended.','package_seconds':time.perf_counter()-start};(D/'ARCHIVE_MANIFEST_20261015_52.json').write_text(json.dumps(manifest,indent=2));print({k:v for k,v in manifest.items() if k!='archives'});print('ARCHIVES',[(x['path'],x['bytes']) for x in archives])
