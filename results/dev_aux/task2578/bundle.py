"""Seal new99 exact source/data once; previous43capsules preserved."""
from pathlib import Path
import ast,hashlib,json,re,zipfile,time
from results.dev_aux.task2542.png_content_review import inspect_png
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 start=time.perf_counter();prior=json.loads((OUT/'ARCHIVE_MANIFEST_20261019_98.json').read_text());assert len(prior['archives'])==43
 for name,h in prior['archives'].items():assert digest(OUT/name)==h,name
 assert json.loads((OUT/'task2576/orchestration-ended.json').read_text())['all_owned_producers_closed']
 files={}
 for task in range(2576,2580):
  for p in(OUT/f'task{task}').rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc','.pyo'):files[p.relative_to(ROOT).as_posix()]=p
 for name in('results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2568/test_training.py','results/dev_aux/task2505/queries.jsonl','results/dev_aux/task2568/verify.py','results/dev_aux/task2571/test_diagnostics.py'):
  files[name]=ROOT/name
 for name in json.loads((OUT/'task2576/plan.json').read_text())['pins']:files[name]=ROOT/name
 for name in('audit.json','signals.json','witness-queries.json','information.json','training-curves.json','search-replay.json','first-targets.json'):assert(OUT/'task2576'/name).is_file(),name
 for name in('result.json','eval-result.json','deployment-audit.json','summary.json','trajectory-divergence.json','terminal-ledger.json'):assert(OUT/'task2577'/name).is_file(),name
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
     if 'alphasho'in dep.as_posix().casefold()or'.local_agent'in dep.parts:continue
     if dep.is_file()and dep.resolve().is_relative_to(ROOT.resolve()):todo.append(dep)
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
 archive=OUT/'DELTA_REPRO_20261019_99.zip';assert not archive.exists()
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True)as z:
  z.writestr('MANIFEST_20261019_99.json',json.dumps(dict(files=manifest,scope='Exact99 prospective matched TRAIN/DEPLOYcontext study, ALL8TDarms/1.5Mpaidnodes each andALL576scheduledEVALslots/all4initials/roles/foes/contextcells, failures/U/missing retained. Fullhistory/reversecredit/policy/cost audits and16 actualsearchwitnessreplays. Approximateq2 notfullquiet; finitebounds notCIs. Prior43capsules unchanged. Externalchess/pytest dependenciesseparate; finalreport/freshreceipt/deliveryoutsideZIP. RawZIPbytepins authoritative; directGit LF/EOFprojection disclosed.'),indent=2))
  for name,p in sorted(files.items()):z.write(p,name)
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None
 assert archive.stat().st_size<99*1024*1024;hashes=dict(prior['archives']);hashes[archive.name]=digest(archive);new=dict(file=archive.name,sha256=hashes[archive.name],bytes=archive.stat().st_size,payloads=len(manifest),uncompressed_bytes=sum(x['bytes']for x in manifest.values()))
 (OUT/'ARCHIVE_MANIFEST_20261019_99.json').write_text(json.dumps(dict(archives=hashes,new_delta=new,prior_manifest='ARCHIVE_MANIFEST_20261019_98.json',scope='44immutablecapsules; previous43hasheschecked, notalloldconsumersrerun.'),indent=2));(OUT/'ARCHIVE_REVIEW_20261019_99.json').write_text(json.dumps(dict(status='PASS_RAW_BYTEPINS_CRC_ACTUAL_CONTENT_REVIEW',**new,prior_unchanged=43,sensitive_hits=0,png_review=png_review,AST_checks=asts,JSON_files=jsons,JSONL_records=lines,seconds=time.perf_counter()-start),indent=2));print(json.dumps(new))
if __name__=='__main__':run()
