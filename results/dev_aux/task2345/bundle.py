"""Seal exact81 sources/data and explicitly unexecuted plans after every started producer closes."""
from pathlib import Path
import json,hashlib,zipfile,ast,re,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run():
 required=['task2330/result.json','task2331/completion.json','task2332/task2331-audit.json','task2333/result.json','task2334/deferred.json','task2337/task2331-result.json','task2339/task2331-result.json','task2349/result.json','task2351/result.json','task2341/result.json','task2344/result.json','task2335/result.json','task2338/result.json','task2350/result.json','task2352/audit.json']
 if(OUT/'task2340/started.json').exists():required+=['task2340/completion.json','task2343/task2340-audit.json','task2342/selection.json','task2347/result.json','task2348/result.json']
 else:required+=['task2340/deferred.json']
 for name in required:
  if not(OUT/name).exists():raise RuntimeError('Requiredclosed81evidencemissing:'+name)
 start=time.perf_counter();prior=json.loads((OUT/'ARCHIVE_MANIFEST_20261017_80.json').read_text());old={};archive_sources={}
 for name,h in prior['archives'].items():
  zpath=OUT/name;assert digest(zpath)==h
  with zipfile.ZipFile(zpath)as z:
   m=json.loads(z.read(next(n for n in z.namelist()if n.startswith('MANIFEST'))));files=m['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
   for name2,entry in files.items():old[name2]=entry;archive_sources[name2]=zpath
 files={}
 for task in range(2330,2353):
  for p in(OUT/f'task{task}').rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc','.pyo'):files[p.relative_to(ROOT).as_posix()]=p
 # All actual byte-pinned dependencies must override old publication projections.
 for task in(2330,2331,2334,2335,2338,2341,2340):
  if not(OUT/f'task{task}/plan.json').exists():continue
  plan=json.loads((OUT/f'task{task}/plan.json').read_text(encoding='utf-8-sig'))
  for name in plan.get('pins',{}):
   pp=ROOT/name;files[pp.relative_to(ROOT).as_posix()]=pp
 for name in('results/dev_aux/task2325/plan.json','tests/conftest.py','tests/rule_semantics_ir_fixtures.py'):
  files[name]=ROOT/name
 # Snapshot the actual local Python import closure; third-party runtime remains
 # the previous source bundle plus explicitly qualified host NumPy.
 todo=[p for p in files.values()if p.suffix=='.py'];seen=set()
 while todo:
  p=todo.pop();name=p.relative_to(ROOT).as_posix()
  if 'alphasho'in name.casefold():raise RuntimeError('Out-of-scope dependency path; stop BEFOREopening')
  if name in seen:continue
  seen.add(name);files[name]=p;tree=ast.parse(p.read_text(encoding='utf-8-sig'))
  for node in ast.walk(tree):
   modules=[]
   if isinstance(node,ast.Import):modules=[a.name for a in node.names]
   elif isinstance(node,ast.ImportFrom):
    if node.level:
     base=list(p.parent.relative_to(ROOT).parts)
     if node.level>1:base=base[:-(node.level-1)]
     prefix='.'.join(base+([]if node.module is None else node.module.split('.')))
    else:prefix=node.module or''
    modules=[prefix]+[prefix+'.'+a.name for a in node.names]
   for mod in modules:
    pp=ROOT.joinpath(*mod.split('.'))
    for found in(pp.with_suffix('.py'),pp/'__init__.py'):
     if 'alphasho'in found.as_posix().casefold():continue
     if found.is_file()and found.resolve().is_relative_to(ROOT.resolve())and '.local_agent'not in found.parts:todo.append(found)
  parent=p.parent
  while parent!=ROOT:
   init=parent/'__init__.py'
   if init.exists():todo.append(init)
   parent=parent.parent
 patterns=[re.compile(rb'(?i)(?:[A-Z]:[/\\]Users[/\\]|/(?:Users|home)/)[^\s"\x27<>|()\[\]]+'),re.compile(rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'),re.compile(rb'(?:xox[baprs]-[A-Za-z0-9-]{15,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')]
 entries={};overrides={};override_review=[];bytes_total=0;ast_checks=0;json_files=0;jsonl_records=0
 for name,p in sorted(files.items()):
  assert p.resolve().is_relative_to(ROOT.resolve())and '.local_agent'not in p.parts
  h=hashlib.sha256();tail=b''
  with p.open('rb')as f:
   for block in iter(lambda:f.read(1024*1024),b''):
    if any(regex.search(tail+block)for regex in patterns):raise RuntimeError('Actualoutgoing sensitivecontent; privateoriginal retained:'+name)
    h.update(block);tail=block[-2048:]
  size=p.stat().st_size;bytes_total+=size;entries[name]=dict(sha256=h.hexdigest(),bytes=size)
  if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'));ast_checks+=1
  elif p.suffix=='.json':json.loads(p.read_text(encoding='utf-8-sig'));json_files+=1
  elif p.suffix=='.jsonl':
   with p.open(encoding='utf-8-sig')as f:
    for line in f:json.loads(line);jsonl_records+=1
  if name in old and old[name]['sha256']!=h.hexdigest():
   overrides[name]=old[name]['sha256']
   with zipfile.ZipFile(archive_sources[name])as z:raw=z.read(name)
   equal=ast.dump(ast.parse(raw.decode('utf-8-sig')))==ast.dump(ast.parse(p.read_text(encoding='utf-8-sig')))if p.suffix=='.py'else json.dumps(json.loads(raw),sort_keys=True)==json.dumps(json.loads(p.read_text(encoding='utf-8-sig')),sort_keys=True)if p.suffix=='.json'else json.dumps([json.loads(x)for x in raw.splitlines()if x],sort_keys=True)==json.dumps([json.loads(x)for x in p.read_text(encoding='utf-8-sig').splitlines()if x],sort_keys=True)if p.suffix=='.jsonl'else raw==p.read_bytes()
   override_review.append(dict(path=name,old_sha=old[name]['sha256'],new_sha=h.hexdigest(),semantic_equal=equal))
   if not equal:raise RuntimeError('Reviewactualsemanticdependencydifference beforesealing:'+name)
 manifest=dict(schema_version=1,files=entries,overrides=overrides,scope='Exactexecuted81sources/closeddata PLUSexplicitunexecuted2334/2336plans/modules; preparedsourceisnotexecutionevidence. DeclaredAST/JSON-equivalentreusedsourceoverlays. Earlier24archivesimmutable. Failedpreflight/source/consumerattemptsretained. No .local_agent/accounts/personalpaths/credentials; actualcontentreview, originnotpublicationban.')
 archive=OUT/'DELTA_REPRO_20261017_81.zip';assert not archive.exists()
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True)as z:
  z.writestr('MANIFEST_20261017_81.json',json.dumps(manifest,indent=2))
  for name,p in sorted(files.items()):z.write(p,name)
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None
 assert archive.stat().st_size<99*1024*1024,'Oversizearchive remains exact; splitreviewedpayloadcopies, do notforceGitblob'
 hashes=dict(prior['archives']);hashes[archive.name]=digest(archive);(OUT/'ARCHIVE_MANIFEST_20261017_81.json').write_text(json.dumps(dict(schema_version=1,archives=hashes,new_delta=dict(file=archive.name,sha256=hashes[archive.name],bytes=archive.stat().st_size,payloads=len(entries),uncompressed_bytes=bytes_total,overrides=overrides),prior_manifest='ARCHIVE_MANIFEST_20261017_80.json',scope='25exactZIPs; new81consumerstagesafterdeclaredsourceoverlays. Prior80qualified24replayremainsitsownhistoricalreceipt; no oldproducer/fitrerun.'),indent=2))
 review=dict(status='PASS_ACTUAL81_PAYLOAD_SENSITIVE_CONTENT_AST_JSON_SHA_AND_CRC',archive=archive.name,archive_sha=hashes[archive.name],bytes=archive.stat().st_size,payloads=len(entries),raw_bytes=bytes_total,sensitive_hits=0,AST_checks=ast_checks,JSON_files=json_files,JSONL_records=jsonl_records,semantic_equivalent_overlays=override_review,seconds=time.perf_counter()-start)
 (OUT/'ARCHIVE_REVIEW_20261017_81.json').write_text(json.dumps(review,indent=2));print(json.dumps({k:v for k,v in review.items()if k!='semantic_equivalent_overlays'}))
if __name__=='__main__':run()
