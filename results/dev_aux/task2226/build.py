"""Seal two exact reviewed deltas; raw sources/data never rewritten after seal."""
from pathlib import Path
import ast,json,re,zipfile,hashlib,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
ROOT=Path.cwd();BASE=ROOT/'results/dev_aux'
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def build():
 for task in(2208,2209,2213,2220,2224,2227):assert (BASE/f'task{task}/completion.json').exists()
 for task in(2214,2216,2217,2221,2222,2223):assert(BASE/f'task{task}/result.json').exists()
 stop=EvidenceStopReader(ROOT);stop();previous=json.loads((BASE/'ARCHIVE_MANIFEST_20261016_75.json').read_text());archives=dict(previous['archives']);infos=[];allreview=[];start=time.perf_counter()
 patterns=dict(email=rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',credential=rb'(?:ghp_|github_pat_|xox[baprs]-|sk-proj-)[A-Za-z0-9_-]{12,}',personal_user_path=rb'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s"\x27]+')
 for label,tasks in(('A',list(range(2208,2221))+[2225,2226,2227]),('B',list(range(2221,2225)))):
  archive=BASE/f'DELTA_REPRO_20261016_76{label}.zip';assert not archive.exists();paths=[]
  for task in tasks:paths.extend(p for p in(BASE/f'task{task}').rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix not in('.pyc','.log'))
  if label=='A':paths.extend(BASE/n for n in('CONTEXT76_PREFIT.json','ARCHIVE_MANIFEST_20261016_75.json'))
  files={};hits=[]
  for p in sorted(set(paths)):
   n=p.relative_to(ROOT).as_posix();assert p.resolve().is_relative_to(ROOT.resolve())and'.local_agent'not in p.parts and p.suffix not in('.db','.sqlite3','.pem','.key')
   tail=b'';size=0;h=hashlib.sha256()
   with p.open('rb')as f:
    for block in iter(lambda:f.read(1024*1024),b''):
     stop();h.update(block);size+=len(block)
     for tag,pattern in patterns.items():
      if re.search(pattern,tail+block):hits.append(dict(path=n,pattern=tag))
     tail=block[-512:]
   if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'))
   if p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'))
   files[n]=dict(sha256=h.hexdigest(),bytes=size)
  assert not hits,hits
  manifest=dict(schema_version=1,files=files,overrides={},scope='Exactexecuted76sources/frozenplans/rawcensuslabels/actualgames/failedattempts/corrections. No privateSlack/accounts/flags/credentials; old13archivesimmutable. Closingreports/replayreceipts/directGittextprojectionsmayfollowseal; rawpinsauthoritative. SamehostPython/OSnotbundled.')
  with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   z.writestr(f'MANIFEST_DELTA_76{label}.json',json.dumps(manifest,indent=2))
   for n in files:
    with(ROOT/n).open('rb')as src,z.open(n,'w',force_zip64=True)as dst:
     for block in iter(lambda:src.read(1024*1024),b''):stop();dst.write(block)
  assert archive.stat().st_size<95*1024*1024,'Gitblobsizeguard; neverpublishoversize'
  with zipfile.ZipFile(archive)as z:
   assert z.testzip()is None
   for n,row in files.items():
    h=hashlib.sha256();size=0
    with z.open(n)as f:
     for block in iter(lambda:f.read(1024*1024),b''):stop();h.update(block);size+=len(block)
    assert h.hexdigest()==row['sha256']and size==row['bytes']
  info=dict(file=archive.name,sha256=digest(archive),bytes=archive.stat().st_size,payloads=len(files),uncompressed_bytes=sum(x['bytes']for x in files.values()));infos.append(info);archives[archive.name]=info['sha256'];allreview.append(dict(archive=archive.name,paths=len(files),patterns=list(patterns),hits=hits));print(json.dumps(info),flush=True)
 result=dict(schema_version=1,archives=archives,new_deltas=infos,prior_manifest='ARCHIVE_MANIFEST_20261016_75.json',scope='15hashpinnedarchives; rawexecutedbytes/pins preserved. Twofixed76deltas, nooverlays/oldcapreset/studyproducerreplay.')
 (BASE/'ARCHIVE_MANIFEST_20261016_76.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(BASE/'ARCHIVE_REVIEW_20261016_76.json').write_text(json.dumps(dict(status='PASS_ACTUAL_CONTENT_SHA_SIZE_CRC_SENSITIVITY',reviews=allreview,seconds=time.perf_counter()-start),indent=2),encoding='utf-8')
if __name__=='__main__':build()
