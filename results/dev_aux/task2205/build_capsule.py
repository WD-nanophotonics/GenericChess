"""Seal reviewed exact75 source/evidence; one build, no old archive rewrites."""
from pathlib import Path
import ast,json,re,zipfile,hashlib
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux';ARCHIVE=OUT/'DELTA_REPRO_20261016_75.zip'
def sha(data):return hashlib.sha256(data).hexdigest()
def build():
 if ARCHIVE.exists():raise RuntimeError('sealedarchive NEVERrewrite')
 for task in(2190,2204,2202):
  v=json.loads((OUT/f'task{task}/completion.json').read_text());assert v['status']in('COMPLETE','PARTIAL_GLOBAL_CAP')
 previous=json.loads((OUT/'ARCHIVE_MANIFEST_20261016_74.json').read_text());prior={}
 for name,digest in previous['archives'].items():
  path=OUT/name;assert sha(path.read_bytes())==digest
  with zipfile.ZipFile(path)as z:
   m=json.loads(z.read(next(n for n in z.namelist()if n.startswith('MANIFEST'))));files=m['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
   for n,row in files.items():prior[n]=row['sha256']
 paths=[]
 for task in range(2186,2208):
  folder=OUT/f'task{task}'
  if folder.exists():paths.extend(p for p in folder.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.suffix not in('.pyc','.log'))
 paths.extend(ROOT/n for n in('tests/product/test_runtime_aux_identity.py','tests/product/test_recombined_semantic_lifecycle.py','results/dev_aux/PROOF_SCOPE_20261016_75.md'))
 paths.extend(ROOT/r['path']for r in json.loads((OUT/'task2207/inventory.json').read_text())['sources'])
 patterns=dict(email=rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',credential=rb'(?:ghp_|github_pat_|xox[baprs]-|sk-proj-)[A-Za-z0-9_-]{12,}',personal_user_path=rb'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s"\x27]+')
 files={};payload={};overrides={};hits=[]
 for path in sorted(set(paths)):
  assert path.resolve().is_relative_to(ROOT.resolve());name=path.relative_to(ROOT).as_posix();data=path.read_bytes()
  assert'.local_agent'not in path.parts and path.suffix not in('.sqlite3','.db','.pem','.key')
  for label,pattern in patterns.items():
   if re.search(pattern,data):hits.append(dict(path=name,pattern=label))
  if path.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
  if path.suffix=='.json':json.loads(data.decode('utf-8-sig'))
  files[name]=dict(sha256=sha(data),bytes=len(data));payload[name]=data
  if name in prior and prior[name]!=sha(data):overrides[name]=prior[name]
 assert not hits,hits
 manifest=dict(schema_version=1,files=files,overrides=overrides,scope='Exactexecuted75sources/rawtraces/closedstudies/failedattempts andexplicitcorrections. No privateSlack/flags/accounts/credentials. Oldtwelvearchives unchanged. Late75reports/replayreceipts/deliverymetadata directGit afterseal, notselfreferential.')
 with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
  z.writestr('MANIFEST_DELTA_75.json',json.dumps(manifest,indent=2))
  for name,data in payload.items():z.writestr(name,data)
 with zipfile.ZipFile(ARCHIVE)as z:
  assert z.testzip()is None
  for n,row in files.items():assert sha(z.read(n))==row['sha256']and len(z.read(n))==row['bytes']
 info=dict(file=ARCHIVE.name,sha256=sha(ARCHIVE.read_bytes()),bytes=ARCHIVE.stat().st_size,payloads=len(files),uncompressed_bytes=sum(r['bytes']for r in files.values()),overrides=overrides)
 new=dict(schema_version=1,archives={**previous['archives'],ARCHIVE.name:info['sha256']},new_delta=info,prior_manifest='ARCHIVE_MANIFEST_20261016_74.json',scope=manifest['scope'])
 (OUT/'ARCHIVE_MANIFEST_20261016_75.json').write_text(json.dumps(new,indent=2),encoding='utf-8');(OUT/'ARCHIVE_REVIEW_20261016_75.json').write_text(json.dumps(dict(status='PASS_ACTUAL_CONTENT_SHA_SIZE_CRC_SENSITIVITY',patterns=list(patterns),hits=hits,**info),indent=2),encoding='utf-8');print(json.dumps(info))
if __name__=='__main__':build()
