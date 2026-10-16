"""Immutable reviewed project source/evidence capsules; no private rawSlack."""
from pathlib import Path
import json,hashlib,zipfile,re
ROOT=Path.cwd();OUT=Path('results/dev_aux');TAG='20261016_70'
def sha(b):return hashlib.sha256(b).hexdigest()
def run():
 assert json.loads(Path('.local_agent/producer70.json').read_text())['state']=='CLOSED'
 assert json.loads(Path('.local_agent/producer70-models.json').read_text())['state']=='CLOSED'
 folders=[Path(f'results/dev_aux/task{i}')for i in range(2054,2087)if Path(f'results/dev_aux/task{i}').is_dir()];files=[p for folder in folders for p in folder.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc','.pyo')]
 sources={}
 with zipfile.ZipFile(OUT/'SOURCE_REPRO_20261016_69.zip')as z:
  for n in z.namelist():
   if not n.startswith('MANIFEST69'):sources[n]=z.read(n)
 for p in list(Path('tools/local_agent').glob('*.py'))+[Path('tests/workflow/test_slack_transport.py')]+[p for p in files if p.suffix in('.py','.ini')]:sources[p.as_posix()]=p.read_bytes()
 evidence={p.as_posix():p.read_bytes()for p in files if p.suffix not in('.py','.ini')}
 # Legacy actual-census inputs required by futurecontrols and restoredaudit.
 for folder in('results/dev_aux/task2044','results/dev_aux/task2045'):
  for p in Path(folder).glob('*'):
   if p.is_file()and p.suffix in('.json','.jsonl'):evidence[p.as_posix()]=p.read_bytes()
 for p in(Path('results/dev_aux/task2036/rules.json'),Path('results/dev_aux/task2048/portable_certificate.py')):
  (sources if p.suffix=='.py'else evidence)[p.as_posix()]=p.read_bytes()
 reviewed=[]
 for name,b in(sources|evidence).items():
  # Source capsules carry vetted public dependency authors/licenses. User/account
  # private originals are NEVER selected; actual newdata are reviewed separately.
  if name.startswith('.local_agent/')or '..'in Path(name).parts or Path(name).is_absolute():raise ValueError('invalidpublicationpath')
  if name.startswith('results/dev_aux/task20'):
   text=b.decode('utf-8',errors='ignore')
   if re.search(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',text)or re.search(r'(?:xox[bp]-|ghp_|github_pat_)[A-Za-z0-9]{15,}',text):raise ValueError('sensitiveoutgoingcontent '+name)
  reviewed.append(name)
 archives=[]
 for kind,payload in(('SOURCE',sources),('EVIDENCE',evidence)):
  path=OUT/(('SOURCE_REPRO_'if kind=='SOURCE'else'EVIDENCE_')+TAG+'.zip');manifest=dict(files={n:dict(bytes=len(b),sha256=sha(b))for n,b in sorted(payload.items())},scope='Reviewedproject-onlypayloads; rawpersonalSlack/account/credentials excluded. Actualsource/data/failures authorized. Sourcebase69 plusnew70overrides; runtimePythonnotbundled. NoclaimNativebinaryrebuild.')
  with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
   for n,b in sorted(payload.items()):z.writestr(n,b)
   z.writestr('MANIFEST70_'+kind+'.json',json.dumps(manifest,indent=2))
  with zipfile.ZipFile(path)as z:
   assert z.testzip()is None
   for n,row in manifest['files'].items():assert sha(z.read(n))==row['sha256']
  archives.append(dict(path=path.as_posix(),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),payloads=len(payload),uncompressed_bytes=sum(map(len,payload.values()))))
 bulky=[p.as_posix()for p in files if p.stat().st_size>1024*1024];ignore=Path('.gitignore')
 with ignore.open('a',encoding='utf-8')as f:f.write('\n# DEV_AUX70 bulky exactpayloads preserved publicly in EVIDENCE70.\n'+'\n'.join('/'+n for n in sorted(bulky))+'\n')
 result=dict(status='PASS_IMMUTABLE_REVIEWED_SOURCE_EVIDENCE_SHA_CRC',archives=archives,large_local_originals_retained=sorted(bulky),new_payload_paths_reviewed=len(files),scope='Bothproducersclosed; Nativeactualrecords, exactteachers, partial/failedcases and allsources retained. Newsource stillrequiresavailableNumPy1.26.4 torefit; independentrestoreaudits do not. No private rawSlack/credentials selected.')
 (OUT/f'ARCHIVE_MANIFEST_{TAG}.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='large_local_originals_retained'}))
if __name__=='__main__':run()
