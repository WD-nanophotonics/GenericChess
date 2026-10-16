"""Immutable segment69 source/evidence closure and actual isolated replay."""
from pathlib import Path
import json,zipfile,subprocess,sys,os,xml.etree.ElementTree as ET
from results.dev_aux.task1989.closure import seal,sha
BASE=Path('results/dev_aux');OUT=BASE/'task2040'
SOURCE=BASE/'SOURCE_REPRO_20261016_69.zip';EVIDENCE=BASE/'EVIDENCE_20261016_69.zip'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def members(archive,manifest):
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  result={}
  for name,row in json.loads(z.read(manifest))['files'].items():
   b=z.read(name);assert sha(b)==row['sha256'];result[name]=b
  return result

def package():
 for task in (2030,2037,2050):assert (BASE/f'task{task}/campaign-completion.json').exists()
 for task in (2033,2034,2035,2038,2039,2042,2043,2044,2046,2047,2051,2052,2053):assert (BASE/f'task{task}/result.json').exists()
 sources=members(BASE/'SOURCE_REPRO_20261016_68.zip','MANIFEST68SOURCE.json')
 sources.update(members(BASE/'RUNTIME_REPRO_SUPPORT_20261016_68.zip','MANIFEST68RUNTIME.json'))
 evidence=members(BASE/'EVIDENCE_20261016_68.zip','MANIFEST68EVIDENCE.json')
 # Preserve prior exact evidence needed by current diagnostic replays. All old archives remain immutable.
 for task in (2030,2033,2034,2035,2036,2037,2038,2039,2040,2042,2043,2044,2045,2046,2047,2048,2049,2050,2051,2052,2053):
  for p in (BASE/f'task{task}').rglob('*'):
   if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.json','.jsonl','.ini') or p.name in ('restore.json',):continue
   evidence[p.as_posix()]=p
   if p.suffix in ('.py','.ini') or p.name in ('rules.json','feasibility.json','study-freeze.json'):sources[p.as_posix()]=p
 for task in (2030,2037,2050):
  for name,digest in read(BASE/f'task{task}/run-plan.json')['source_sha'].items():
   p=Path(name);assert sha(p.read_bytes())==digest;sources[p.as_posix()]=p
 a=seal(SOURCE,sources,'MANIFEST69SOURCE.json','Exact68 Core/proof/GPL/realpytest/chess source plus historical runtime support and ALL69 executed code, frozen inputs/pins. No Nativebinary/compiler/rawSlack. SameOS/interpreter.')
 b=seal(EVIDENCE,evidence,'MANIFEST69EVIDENCE.json','All closed69 actualrecords/Nativejournals/locks/audits plus exact68 evidence required by existing-record diagnostics. No personalaccount/credentials; archives immutable, late report/session/restore directGit.')
 save(BASE/'ARCHIVE_MANIFEST_20261016_69.json',dict(status='SEALED_CRC_ALL_PAYLOAD_SHA',archives=[a,b]));print(json.dumps([a,b]),flush=True)

def restore():
 dest=Path('.local_agent/repro69').resolve();dest.mkdir(exist_ok=False);(dest/'rechecks').mkdir()
 for arc,manifest in ((SOURCE,'MANIFEST69SOURCE.json'),(EVIDENCE,'MANIFEST69EVIDENCE.json')):
  for name,b in members(arc,manifest).items():
   assert not Path(name).is_absolute() and '..'not in Path(name).parts
   p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
   if p.exists():assert p.read_bytes()==b,name
   else:p.write_bytes(b)
 env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
 common="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));"
 def execute(code,log,timeout):
  r=subprocess.run([sys.executable,'-S','-c',code],cwd=dest,env=env,capture_output=True,timeout=timeout);(dest/log).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode(errors='replace');return r
 execute(common+"import pytest,chess,generic_chess;assert all(pathlib.Path(m.__file__).is_relative_to(root)for m in(pytest,chess,generic_chess));print('PASS_ACTUAL_DEPENDENCY_PREFLIGHT')",'preflight.log',30)
 execute(common+"import pytest;raise SystemExit(pytest.main(['results/dev_aux/task2030/test_schedule.py','results/dev_aux/task2037/test_schedule.py','results/dev_aux/task2050/test_schedule.py','-q','--import-mode=importlib','--basetemp=rechecks/pytest69','--junitxml=tests69.xml']))",'tests.log',60)
 xml=ET.parse(dest/'tests69.xml').getroot();suites=list(xml)if xml.tag=='testsuites'else[xml];tests={k:sum(int(x.attrib.get(k,0))for x in suites)for k in ('tests','failures','errors','skipped')};assert tests==dict(tests=5,failures=0,errors=0,skipped=0)
 replay=common+"""start=time.perf_counter()
import results.dev_aux.task2033.counterexample as a
import results.dev_aux.task2034.audit as b
import results.dev_aux.task2035.cost_density as c
import results.dev_aux.task2038.audit as d
import results.dev_aux.task2039.mechanism as e
import results.dev_aux.task2042.identifiability as f
import results.dev_aux.task2043.inventory_cost as g
import results.dev_aux.task2045.coverage as h
import results.dev_aux.task2048.portable_certificate as i
import results.dev_aux.task2051.audit as j
import results.dev_aux.task2053.audit as k
for n,m in enumerate((a,b,c,d,e,f,g,h,i,j,k)):
 target=root/'rechecks'/str(n);target.mkdir()
 if hasattr(m,'OUT'):m.OUT=target
 if hasattr(m,'O'):m.O=target
 if hasattr(m,'OUT') and hasattr(m,'O'):m.OUT=m.O=target
a.run();b.main();c.main();d.run();e.main();f.main();g.main();h.main();i.verify();j.main();k.main()
p=json.loads((b.OUT/'result.json').read_text())['physical'];q=json.loads((d.OUT/'result.json').read_text())['physical'];z=json.loads((j.OUT/'result.json').read_text())['physical']
assert all(not getattr(m,'__file__',None)or pathlib.Path(m.__file__).is_relative_to(root)for name,m in sys.modules.items()if name.startswith(('generic_chess','scripts.','results.','chess','pytest')))
print(json.dumps(dict(status='PASS_ALL69_SOURCE_ONLY_REPLAY',new_fromroot_games=p['games']+q['games']+z['games'],new_moves=p['moves']+q['moves']+z['moves'],new_native_bindings=p['actual_native']+q['actual_native']+z['actual_native'],proof_adopting_actual_wins=p['proof_games']+q['proof_games']+z['proof_games'],newcensus_covered_states=json.loads((h.OUT/'coverage.json').read_text())['admissible_by_inventory'],portable_certificate_edges=json.loads((i.OUT/'replay.json').read_text())['independent_transition_count'],proof_coverage_receipts=json.loads((k.OUT/'result.json').read_text())['queries'],seconds=time.perf_counter()-start,new_Native_or_PN_or_search_calls=0)))"""
 r=execute(replay,'replay.log',240);summary=json.loads(r.stdout.decode().splitlines()[-1]);save(OUT/'restore.json',dict(status='PASS_NEW_DIRECTORY_SOURCE_ONLY_RESTORE',tests=tests,replay=summary,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Fresh private directory/Python-S/actual restored pytest,chess,Core and sources; module-path assertions; samehostOS/interpreter, noNative rebuild or newfitness.'))
 print(json.dumps(summary),flush=True)
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
