"""Seal new95 exact source/data once; previous39capsules preserved."""
from pathlib import Path
import ast,hashlib,json,re,zipfile,time
from results.dev_aux.task2542.png_content_review import inspect_png
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 start=time.perf_counter();prior=json.loads((OUT/'ARCHIVE_MANIFEST_20261019_94.json').read_text());assert len(prior['archives'])==39
 for name,h in prior['archives'].items():assert digest(OUT/name)==h,name
 for name in('task2558/result.json','task2559/result.json','task2560/training-audit.json','task2560/deployment.json','task2560/unpruned.json','task2560/signals.json','task2560/design-costs.json','task2560/reference.json','task2562/result.json','task2563/result.json','task2564/training-audit.json','task2564/deployment.json','task2564/design-costs.json','task2564/unpruned.json'):assert(OUT/name).is_file(),name
 files={}
 for task in range(2558,2565):
  for p in(OUT/f'task{task}').rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc','.pyo'):files[p.relative_to(ROOT).as_posix()]=p
 for name in('METHOD_20261019_95.md','TESTS_20261019_95.json','JOURNAL_ROUTES_20261019_95.json','FIGURE_REVIEW_20261019_95.json'):files['results/dev_aux/'+name]=OUT/name
 # Old TRAIN only, required for independently recomputed clockreference, no DEV rewards.
 for name in('results/dev_aux/task2546/result.json','results/dev_aux/task2546/plan.json','results/dev_aux/task2546/queries.jsonl','results/dev_aux/task2557/signal-baseline-check.json'):files[name]=ROOT/name
 for n,p in list(files.items()):
  if p.suffix=='.json':
   data=json.loads(p.read_text(encoding='utf-8-sig'))
   if isinstance(data,dict):
    for dep in data.get('pins',{}):
     actual=ROOT/dep;files[actual.relative_to(ROOT).as_posix()]=actual
 for name in('results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2505/queries.jsonl','results/dev_aux/task2523/test_exposure.py','results/dev_aux/task2546/test_learning.py','results/dev_aux/task2558/test_clock.py'):files[name]=ROOT/name
 todo=[p for p in files.values()if p.suffix=='.py'];seen=set()
 while todo:
  p=todo.pop();name=p.relative_to(ROOT).as_posix();assert 'alphasho'not in name.casefold()
  if name in seen:continue
  seen.add(name);files[name]=p
  for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
   mods=[]
   if isinstance(node,ast.Import):mods=[a.name for a in node.names]
   elif isinstance(node,ast.ImportFrom):
    if node.level:
     parts=list(p.parent.relative_to(ROOT).parts)
     if node.level>1:parts=parts[:-(node.level-1)]
     prefix='.'.join(parts+([]if node.module is None else node.module.split('.')))
    else:prefix=node.module or''
    mods=[prefix]+[prefix+'.'+a.name for a in node.names]
   for mod in mods:
    pp=ROOT.joinpath(*mod.split('.'))
    for dep in(pp.with_suffix('.py'),pp/'__init__.py'):
     if dep.is_file()and dep.resolve().is_relative_to(ROOT.resolve())and '.local_agent'not in dep.parts and 'alphasho'not in dep.as_posix().casefold():todo.append(dep)
  parent=p.parent
  while parent!=ROOT:
   if(parent/'__init__.py').exists():todo.append(parent/'__init__.py')
   parent=parent.parent
 patterns=[re.compile(rb'(?i)(?:[A-Z]:[/\\]Users[/\\]|/(?:Users|home)/)[^\s"\x27<>|()\[\]]+'),re.compile(rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'),re.compile(rb'(?:xox[baprs]-[A-Za-z0-9-]{15,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})')];manifest={};png_review={};asts=jsons=lines=0
 for name,p in sorted(files.items()):
  if p.suffix=='.jsonl':
   h=hashlib.sha256();size=0
   with p.open('rb')as f:
    for rawline in f:
     assert not any(rx.search(rawline)for rx in patterns),name;json.loads(rawline);h.update(rawline);size+=len(rawline);lines+=1
   manifest[name]=dict(sha256=h.hexdigest(),bytes=size);continue
  raw=p.read_bytes()
  if p.suffix=='.png':png_review[name]=inspect_png(raw,patterns)
  else:assert not any(rx.search(raw)for rx in patterns),name
  manifest[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
  if p.suffix=='.py':ast.parse(raw.decode('utf-8-sig'));asts+=1
  elif p.suffix=='.json':json.loads(raw);jsons+=1
  elif p.suffix=='.jsonl':
   for line in raw.splitlines():json.loads(line);lines+=1
 archive=OUT/'DELTA_REPRO_20261019_95.zip';assert not archive.exists()
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True)as z:
  z.writestr('MANIFEST_20261019_95.json',json.dumps(dict(files=manifest,scope='Exact95 prospectively registered Mean versus CostClock TRAIN/all32arms plus original384newfixedfoeD3deployments and separatelyregistered16constantRatearms/NEW512all4modelslots/all50controls/independenttypedclockcredit+gradient/outcome audits/32unprunedrootwitnesses+interiorboundchecks/oldTRAINreference recount; old39capsules immutable. Externalchess/pytest/plot deps installed separately. Sourcepins refer exactZIPbytes; directGittext mayLFnormalize. Final humanreport/cost/freshreceipt/deliveryverification are separate directGitmetadata outsideZIP toavoidcircularselfreference; no algorithm/data update.'),indent=2))
  for name,p in sorted(files.items()):z.write(p,name)
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None
 assert archive.stat().st_size<99*1024*1024;hashes=dict(prior['archives']);hashes[archive.name]=digest(archive);new=dict(file=archive.name,sha256=hashes[archive.name],bytes=archive.stat().st_size,payloads=len(manifest),uncompressed_bytes=sum(x['bytes']for x in manifest.values()))
 (OUT/'ARCHIVE_MANIFEST_20261019_95.json').write_text(json.dumps(dict(archives=hashes,new_delta=new,prior_manifest='ARCHIVE_MANIFEST_20261019_94.json',scope='40immutablecapsules; previous39hasheschecked, notalloldconsumersrerun.'),indent=2));(OUT/'ARCHIVE_REVIEW_20261019_95.json').write_text(json.dumps(dict(status='PASS_RAW_BYTEPINS_CRC_ACTUAL_CONTENT_REVIEW',**new,prior_unchanged=39,sensitive_hits=0,png_review=png_review,AST_checks=asts,JSON_files=jsons,JSONL_records=lines,seconds=time.perf_counter()-start),indent=2));print(json.dumps(new))
if __name__=='__main__':run()
