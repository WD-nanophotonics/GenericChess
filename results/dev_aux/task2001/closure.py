"""Immutable source/data capsules and isolated replay for segment67."""
from pathlib import Path
import json,zipfile,subprocess,sys,os,xml.etree.ElementTree as ET
from results.dev_aux.task1989.closure import seal,sha,clean
BASE=Path('results/dev_aux');OUT=BASE/'task2001'
SOURCE=BASE/'SOURCE_REPRO_20261016_67.zip';EVIDENCE=BASE/'EVIDENCE_20261016_67.zip'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def package():
 assert read(BASE/'task1997/campaign-completion.json')['status']=='COMPLETE'
 assert read(BASE/'task1998/result.json')['status']=='PASS_COMMON_POLICY_FRESH_LEARNING'
 assert read(BASE/'task2003/completion.json')['status']=='COMPLETE'
 assert read(BASE/'task2006/result.json')['status'] in ('PASS_PREDECLARED_CONDITIONAL_H48','PARTIAL_CONDITIONAL_H48_RETAINED')
 assert read(BASE/'task2012/result.json')['status'] in ('PASS_PREDECLARED_ACTUAL_RULE_COMPLETION','PARTIAL_ACTUAL_RULE_COMPLETION_RETAINED')
 assert read(BASE/'task2010/result.json')['status']=='PASS_ALL_KRNB_NATIVE_FEASIBILITY_RECEIPTS'
 assert read(BASE/'task2013/result.json')['status']=='PASS_ACTUAL_TRAJECTORY_COST_ATTRIBUTION'
 assert read(BASE/'task2014/result.json')['status']=='PROPOSAL_CHECKED_NOT_ADOPTED'
 assert read(BASE/'task2004/result.json')['status']=='PASS_BOTH_ACTOR_COMMON1K_FILTER_COST'
 sources={};evidence={}
 for name,manifest,digest in [('SOURCE_REPRO_20261016_66.zip','MANIFEST66SOURCE.json','00dd5139e9380d6314d55affef06c548f1c004e2dfa207e1463b48763d81295e'),('RUNTIME_REPRO_SUPPORT_20261016_66.zip','MANIFEST66RUNTIME.json','5d1be642b4e284cf2683b61032fd01cf0c2ef5ded289e2bb0a31cb6673c03349')]:
  arc=BASE/name;assert sha(arc.read_bytes())==digest
  with zipfile.ZipFile(arc) as z:
   assert z.testzip() is None
   for n,v in json.loads(z.read(manifest))['files'].items():
    b=z.read(n);assert sha(b)==v['sha256'];sources[n]=b
 for task in range(1996,2016):
  for p in (BASE/f'task{task}').rglob('*'):
   if not p.is_file() or '__pycache__' in p.parts or p.suffix not in ('.py','.json','.jsonl','.ini') or p.name=='restore.json':continue
   evidence[p.as_posix()]=p
   if p.suffix in ('.py','.ini') or p.name in ('rules.json','feasibility.json','study-freeze.json'):sources[p.as_posix()]=p
 for name,digest in read(BASE/'task1997/run-plan.json')['source_sha'].items():
  p=Path(name);assert sha(p.read_bytes())==digest;sources[p.as_posix()]=p
 a=seal(SOURCE,sources,'MANIFEST67SOURCE.json','Exact66 Core/proof/GPL/test source, real purePython chess and ALL67 source/pins/inputs. No Nativebinary/compiler/privateSlack. Late report/session directGit.')
 b=seal(EVIDENCE,evidence,'MANIFEST67EVIDENCE.json','All closed67 plans/actual publicrecords/Nativejournals/locks/audits/failures. ExactNativejournals archive-only, never deleted. No personalaccount data.')
 save(BASE/'ARCHIVE_MANIFEST_20261016_67.json',dict(status='SEALED_CRC_ALL_PAYLOAD_SHA',archives=[a,b]));print(json.dumps([a,b]),flush=True)
def restore():
 dest=Path('.local_agent/repro67').resolve();dest.mkdir(exist_ok=False);(dest/'rechecks').mkdir()
 for arc,manifest in ((SOURCE,'MANIFEST67SOURCE.json'),(EVIDENCE,'MANIFEST67EVIDENCE.json')):
  with zipfile.ZipFile(arc) as z:
   assert z.testzip() is None
   for name,row in json.loads(z.read(manifest))['files'].items():
    assert not Path(name).is_absolute() and '..'not in Path(name).parts
    b=z.read(name);assert sha(b)==row['sha256'];p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==b,name
    else:p.write_bytes(b)
 env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTEST_ADDOPTS='')
 common="import sys,pathlib,json,time;root=pathlib.Path.cwd();sys.path.insert(0,str(root/'.venv/Lib/site-packages'));"
 preflight=common+"import pytest,chess,generic_chess;import results.dev_aux.task1998.audit,results.dev_aux.task1999.train_stability,results.dev_aux.task2000.identifiability;assert all(pathlib.Path(m.__file__).is_relative_to(root) for m in (pytest,chess,generic_chess));print('PASS_ACTUAL_DEPENDENCY_PREFLIGHT')"
 def execute(code,log,timeout):
  r=subprocess.run([sys.executable,'-S','-c',code],cwd=dest,env=env,capture_output=True,timeout=timeout);(dest/log).write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr.decode(errors='replace');return r
 execute(preflight,'preflight.log',30)
 execute(common+"import pytest;raise SystemExit(pytest.main(['results/dev_aux/task1997/test_schedule.py','results/dev_aux/task1998/test_audit.py','-q','--basetemp=rechecks/pytest67','--junitxml=tests67.xml']))",'tests.log',60)
 xml=ET.parse(dest/'tests67.xml').getroot();suites=list(xml)if xml.tag=='testsuites'else[xml];tests={k:sum(int(x.attrib.get(k,0))for x in suites)for k in ('tests','failures','errors','skipped')};assert tests==dict(tests=3,failures=0,errors=0,skipped=0)
 replay=common+'''start=time.perf_counter()
import results.dev_aux.task1998.audit as a
import results.dev_aux.task1999.train_stability as b
import results.dev_aux.task2000.identifiability as c
import results.dev_aux.task2004.audit as d
import results.dev_aux.task2006.audit as e
import results.dev_aux.task2012.audit as f
import results.dev_aux.task2010.audit as g
import results.dev_aux.task2008.tie_diagnosis as h
import results.dev_aux.task2013.cost_attribution as i
import results.dev_aux.task2014.zero_return_question as j
for n,m in enumerate((a,b,c,d,e,f,g,h,i,j)):
 m.OUT=root/'rechecks'/str(n);m.OUT.mkdir()
a.run();b.main();c.run();d.run();e.run();f.run();g.run();h.run();i.run();j.run()
x=json.loads((a.OUT/'result.json').read_text());p=x['physical'];q=json.loads((d.OUT/'result.json').read_text())['physical'];z=json.loads((e.OUT/'result.json').read_text())['physical'];zz=json.loads((f.OUT/'result.json').read_text())['physical'];bq=json.loads((g.OUT/'result.json').read_text())
assert all(not getattr(m,'__file__',None)or pathlib.Path(m.__file__).is_relative_to(root)for name,m in sys.modules.items()if name.startswith(('generic_chess','scripts.','results.','chess','pytest')))
print(json.dumps(dict(status='PASS_ALL67_SOURCE_ONLY_REPLAY',new_fromroot_games=p['games']+q['games'],H48_parent_cases=z['games'],FULLrule_parent_cases=zz['games'],new_moves=p['moves']+q['moves']+z['moves']+zz['moves'],new_native_bindings=p['actual_native']+q['actual_native']+z['actual_native']+zz['actual_native'],KRNB_qualification_queries=bq['queries'],KRNB_qualification_perfts=bq['perfts'],proof_adopting_actual_wins=p['proof_games']+q['proof_games']+z['proof_games']+zz['proof_games'],seconds=time.perf_counter()-start,new_Native_or_PN_or_search_calls=0)))'''
 r=execute(replay,'replay.log',180);summary=json.loads(r.stdout.decode().splitlines()[-1])
 save(OUT/'restore.json',dict(status='PASS_NEW_DIRECTORY_SOURCE_ONLY_RESTORE',tests=tests,replay=summary,source_sha256=sha(SOURCE.read_bytes()),evidence_sha256=sha(EVIDENCE.read_bytes()),scope='Newprivate directory/Python-S/realrestoredpytest+chess+Core/code/data/modulepathassertions; samehostOS/interpreter, no rebuiltNative or newgames. Execution bytes preserved.'))
 print(json.dumps(summary),flush=True)
if __name__=='__main__':{'package':package,'restore':restore}[sys.argv[1]]()
