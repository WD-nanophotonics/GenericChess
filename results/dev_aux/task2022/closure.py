"""Immutable source/data capsules and isolated replay for segment68."""
from pathlib import Path
import json,zipfile,subprocess,sys,os,xml.etree.ElementTree as ET
from results.dev_aux.task1989.closure import seal,sha,clean
BASE=Path('results/dev_aux');OUT=BASE/'task2022'
SOURCE=BASE/'SOURCE_REPRO_20261016_68.zip';EVIDENCE=BASE/'EVIDENCE_20261016_68.zip'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def package():
 assert read(BASE/'task2016/campaign-completion.json')['status'] in ('COMPLETE','GLOBAL_CAP','INCOMPLETE_OUTCOME')
 assert read(BASE/'task2020/campaign-completion.json')['status'] in ('COMPLETE','GLOBAL_CAP','INCOMPLETE_OUTCOME')
 assert read(BASE/'task2017/result.json')['status']=='PASS_REAL_PLAYER_FAULT_AND_PROGRESS_CONTROLS'
 assert (BASE/'task2018/result.json').exists() and (BASE/'task2021/result.json').exists()
 assert read(BASE/'task2026/result.json')['status']=='PASS_ALL_KRNB_NATIVE_FEASIBILITY_RECEIPTS'
 assert (BASE/'task2027/campaign-completion.json').exists() and (BASE/'task2028/result.json').exists()
 sources={};evidence={}
 for name,manifest,digest in [('SOURCE_REPRO_20261016_67.zip','MANIFEST67SOURCE.json','fba046207e0300f2c4e773de15f3582e566016b7bd69f8fa07c372c2c129ce9e')]:
  arc=BASE/name;assert sha(arc.read_bytes())==digest
  with zipfile.ZipFile(arc) as z:
   assert z.testzip() is None
   for n,v in json.loads(z.read(manifest))['files'].items():
    b=z.read(n);assert sha(b)==v['sha256'];sources[n]=b
 sources['results/dev_aux/task2014/result.json']=BASE/'task2014/result.json'
 for task in range(2016,2030):
  for p in (BASE/f'task{task}').rglob('*'):
   if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.json','.jsonl','.ini') or p.name=='restore.json':continue
   evidence[p.as_posix()]=p
   if p.suffix in ('.py','.ini') or p.name in ('rules.json','feasibility.json','study-freeze.json'):sources[p.as_posix()]=p
 for name,digest in {**read(BASE/'task2016/run-plan.json')['source_sha'],**read(BASE/'task2020/run-plan.json')['source_sha'],**read(BASE/'task2027/run-plan.json')['source_sha']}.items():
  p=Path(name);assert sha(p.read_bytes())==digest;sources[p.as_posix()]=p
 a=seal(SOURCE,sources,'MANIFEST68SOURCE.json','Exact67 Core/proof/GPL/test source, real purePython chess and ALL68 source/pins/inputs. No Nativebinary/compiler/privateSlack. Late report/session directGit.')
 b=seal(EVIDENCE,evidence,'MANIFEST68EVIDENCE.json','All closed68 plans/actual publicrecords/Nativejournals/locks/audits/failures. ExactNativejournals archive-only, never deleted. No personalaccount data.')
 save(BASE/'ARCHIVE_MANIFEST_20261016_68.json',dict(status='SEALED_CRC_ALL_PAYLOAD_SHA',archives=[a,b]));print(json.dumps([a,b]),flush=True)
def restore():
 dest=Path('.local_agent/repro68').resolve();dest.mkdir(exist_ok=False);(dest/'rechecks').mkdir()
 for arc,manifest in ((SOURCE,'MANIFEST68SOURCE.json'),(EVIDENCE,'MANIFEST68EVIDENCE.json')):
  with zipfile.ZipFile(arc) as z:
   assert z.testzip() is None
   for name,row in json.loads(z.read(manifest))['files'].items():
    assert not Path(name).is_absolute() and '..'not in Path(name).parts
    b=z.read(name);assert sha(b)==row['sha256'];p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==b,name
    else:p.write_bytes(b)
 env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
 common="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));"
 preflight=common+"import pytest,chess,generic_chess;import results.dev_aux.task2018.audit,results.dev_aux.task2021.audit,results.dev_aux.task2017.fault_control;assert all(pathlib.Path(m.__file__).is_relative_to(root) for m in (pytest,chess,generic_chess));print('PASS_ACTUAL_DEPENDENCY_PREFLIGHT')"
 def execute(code,log,timeout):
  r=subprocess.run([sys.executable,'-S','-c',code],cwd=dest,env=env,capture_output=True,timeout=timeout);(dest/log).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode(errors='replace');return r
 execute(preflight,'preflight.log',30)
 execute(common+"import pytest;raise SystemExit(pytest.main(['results/dev_aux/task2016/test_schedule.py','results/dev_aux/task2020/test_schedule.py','-q','--basetemp=rechecks/pytest68','--junitxml=tests68.xml']))",'tests.log',60)
 xml=ET.parse(dest/'tests68.xml').getroot();suites=list(xml)if xml.tag=='testsuites'else[xml];tests={k:sum(int(x.attrib.get(k,0))for x in suites)for k in ('tests','failures','errors','skipped')};assert tests==dict(tests=6,failures=0,errors=0,skipped=0)
 replay=common+'''start=time.perf_counter()
import results.dev_aux.task2018.audit as a
import results.dev_aux.task2021.audit as b
import results.dev_aux.task2017.fault_control as c
import results.dev_aux.task2023.training_stability as d
import results.dev_aux.task2026.audit as e
import results.dev_aux.task2028.audit as f
for n,m in enumerate((a,b,c,d,e,f)):
 m.OUT=root/'rechecks'/str(n);m.OUT.mkdir()
a.run();b.run();c.run();d.run();e.run();f.run()
x=json.loads((a.OUT/'result.json').read_text());y=json.loads((b.OUT/'result.json').read_text());p=x['physical'];q=y['physical'];z=json.loads((f.OUT/'result.json').read_text())['physical']
assert all(not getattr(m,'__file__',None)or pathlib.Path(m.__file__).is_relative_to(root)for name,m in sys.modules.items()if name.startswith(('generic_chess','scripts.','results.','chess','pytest')))
print(json.dumps(dict(status='PASS_ALL68_SOURCE_ONLY_REPLAY',new_fromroot_games=p['games']+q['games']+z['games'],new_moves=p['moves']+q['moves']+z['moves'],new_native_bindings=p['actual_native']+q['actual_native']+z['actual_native'],KRNB6_qualification_queries=json.loads((e.OUT/'result.json').read_text())['queries'],KRNB6_qualification_perfts=json.loads((e.OUT/'result.json').read_text())['perfts'],fault_controls=2,legalprogress_control_newmoves=json.loads((c.OUT/'result.json').read_text())['normal_progress']['new_moves'],proof_adopting_actual_wins=p['proof_games']+q['proof_games']+z['proof_games'],seconds=time.perf_counter()-start,new_Native_or_PN_or_search_calls=0)))'''
 r=execute(replay,'replay.log',240);summary=json.loads(r.stdout.decode().splitlines()[-1])
 save(OUT/'restore.json',dict(status='PASS_NEW_DIRECTORY_SOURCE_ONLY_RESTORE',tests=tests,replay=summary,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Newprivate directory/Python-S/realrestoredpytest+chess+Core/code/data/modulepathassertions; samehostOS/interpreter, no rebuiltNative or newgames. Execution bytes preserved.'))
 print(json.dumps(summary),flush=True)
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
