"""Exact checked source/evidence closure and independent same-OS restore."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,os,re
OUT=Path('results/dev_aux');HERE=OUT/'task1906'
SOURCE=OUT/'SOURCE_REPRO_20261015_62.zip';EVIDENCE=OUT/'EVIDENCE_20261015_62.zip'
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(files):
 markers=json.loads(Path('.local_agent/publication_exclusions59.json').read_text())
 for name,data in files.items():
  assert not name.startswith('.local_agent/') and '..' not in Path(name).parts and not Path(name).is_absolute()
  assert all(v.encode() not in data for m in markers for v in (m,m.replace('\\','/'),json.dumps(m)[1:-1])),name
  assert not re.search(rb'(?:xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',data),name

def seal(path,files,manifest_name,scope):
 clean(files);manifest=dict(files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())},scope=scope)
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
  z.writestr(manifest_name,json.dumps(manifest,indent=2))
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for n,r in manifest['files'].items():assert sha(z.read(n))==r['sha256']
 return dict(archive=path.as_posix(),files=len(files),raw_bytes=sum(map(len,files.values())),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),manifest=manifest_name)

def package():
 files={}
 with zipfile.ZipFile(OUT/'SOURCE_REPRO_FINAL_20261015_61.zip') as z:
  for n in z.namelist():
   if n.endswith('/') or 'MANIFEST' in Path(n).name.upper():continue
   files[n]=Path(n).read_bytes() if Path(n).is_file() and Path(n).suffix!='.json' else z.read(n)
 for n in ['scripts/generic_inventory_proof_filter.py','tests/development/test_generic_inventory_proof_filter.py']:
  files[n]=Path(n).read_bytes()
 for task in range(1883,1907):
  for p in (OUT/f'task{task}').rglob('*'):
   if p.is_file() and p.suffix in ('.py','.ini') and '__pycache__' not in p.parts:files[p.as_posix()]=p.read_bytes()
 for n in ['results/dev_aux/task1895/plan.json','results/dev_aux/task1895/result.json','results/dev_aux/task1895/states.jsonl','results/dev_aux/task1896/coverage.json','results/dev_aux/task1897/actual_records.json']:
  files[n]=Path(n).read_bytes()
 source=seal(SOURCE,files,'MANIFEST62SOURCE.json','Exactcurrentresearchsource/27testmodules/313tests/purePython dependencies and requiredactualtestcensus/records. ExistingOS/interpreter, no Native executable/compiler/privateSlack. Closeddata/auditorinputs separately EVIDENCE62; together completeclosure. Historical sourcepins remain immutable.')
 evidence={}
 for task in [1881]+list(range(1883,1907)):
  for p in (OUT/f'task{task}').rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json','.jsonl','.ini') and '__pycache__' not in p.parts:evidence[p.as_posix()]=p.read_bytes()
 for n in ['results/dev_aux/task1872/rules.json','results/dev_aux/task1872/feasibility.json','results/dev_aux/task1862/qualification.json','results/dev_aux/task1877/games.jsonl','results/dev_aux/task1880/plan.json','results/dev_aux/task1880/result.json']:
  evidence[n]=Path(n).read_bytes()
 ev=seal(EVIDENCE,evidence,'MANIFEST62EVIDENCE.json','Closed496physicalpolicygames/10435moves/8763Nativego, fullrecords/receipts/plans/allnewauditors, completeCorecensus/failedmetadata/changedpremise diagnostics and oldboundedreplaydependencies. No privateSlack/accountoutputs/binaries. Sealedbeforeacceptedresearchfinish; finalreport/QA/session/delivery live in directGit, not implied inside this immutablearchive.')
 with (OUT/'ARCHIVE_MANIFEST_20261015_62.json').open('x') as f:json.dump(dict(status='SEALED_CRC_ALL_MEMBER_SHA',archives=[source,ev]),f,indent=2)
 print(json.dumps(dict(source=source,evidence=ev)))

def restore():
 destination=Path('.local_agent/repro62').resolve();destination.mkdir(exist_ok=False);manifests=[]
 for path,mname in ((SOURCE,'MANIFEST62SOURCE.json'),(EVIDENCE,'MANIFEST62EVIDENCE.json')):
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None;manifest=json.loads(z.read(mname));manifests.append(manifest)
   for name,row in manifest['files'].items():
    assert '..' not in Path(name).parts and not Path(name).is_absolute();data=z.read(name);assert sha(data)==row['sha256'];p=destination/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==data
    else:p.write_bytes(data)
 targets=sorted(n for n in manifests[0]['files'] if n.startswith('tests/development/test_') and n.endswith('.py'));assert len(targets)==27
 boot="import sys,pathlib;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));import pytest,generic_chess;assert pathlib.Path(pytest.__file__).is_relative_to(root);assert pathlib.Path(generic_chess.__file__).is_relative_to(root);code=pytest.main("+repr(targets+['-q','--junitxml=restored-tests.xml'])+");assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','_pytest','pytest')));raise SystemExit(code)"
 env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['PYTEST_ADDOPTS']=''
 proc=subprocess.run([sys.executable,'-S','-c',boot],cwd=destination,env=env,capture_output=True,timeout=120);(destination/'tests.log').write_bytes(proc.stdout+proc.stderr)
 import xml.etree.ElementTree as ET
 xml=ET.parse(destination/'restored-tests.xml').getroot();suites=list(xml) if xml.tag=='testsuites' else [xml];counts={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ('tests','failures','errors','skipped')};assert proc.returncode==0 and counts['tests']==313 and counts['failures']==counts['errors']==0
 replay="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));start=time.perf_counter();from results.dev_aux.task1883.audit import audit as a;from results.dev_aux.task1891.audit import audit as b;from results.dev_aux.task1900.filter_audit import audit as c;from results.dev_aux.task1902.horizon_audit import audit as d;from results.dev_aux.task1905.range_audit import audit as e;rows=[f('results/dev_aux/task'+str(t)) for f,t in ((a,1881),(b,1890),(c,1898),(d,1899),(e,1904))];assert sum(r['games'] for r in rows)==496 and sum(r['moves'] for r in rows)==10435;assert all(not getattr(m,'__file__',None) or pathlib.Path(m.__file__).is_relative_to(root) for n,m in sys.modules.items() if n.startswith(('generic_chess','scripts.','results.')));print(json.dumps(dict(status='PASS_ALL_ARCHIVED_ACTUAL_POLICY_REPLAYS',games=496,moves=10435,native_bindings=sum(r['actual_native'] for r in rows),proof_games=sum(r['proof_games'] for r in rows),seconds=time.perf_counter()-start,new_search_or_proof_or_Native_calls=0)))"
 pr=subprocess.run([sys.executable,'-S','-c',replay],cwd=destination,env=env,capture_output=True,timeout=120);(destination/'replay.log').write_bytes(pr.stdout+pr.stderr);assert pr.returncode==0,pr.stderr.decode(errors='replace');rr=json.loads(pr.stdout)
 out=dict(status='PASS_INDEPENDENT_SOURCE_AND_EVIDENCE_RESTORE',counts=counts,replay=rr,source_sha=sha(SOURCE.read_bytes()),evidence_sha=sha(EVIDENCE.read_bytes()),scope='ExistingOS/interpreter,-S,newdirectory/restoredpytestdeps/modulepathassertions. No originalprojectimports/freshmachine/Nativefullrerun. EveryactualCoreedge/fullhistory/rank/Nativecommandbinding replayed, not just summaries.')
 with (HERE/'restore.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
