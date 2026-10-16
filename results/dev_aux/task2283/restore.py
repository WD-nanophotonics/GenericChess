"""Fresh18archive replay of NEW77 closed evidence, no study producer/refit."""
from pathlib import Path
import json,zipfile,hashlib,subprocess,sys,os,time,uuid,xml.etree.ElementTree as ET
root=Path.cwd();m=json.loads((root/'results/dev_aux/ARCHIVE_MANIFEST_20261016_78_FINAL.json').read_text());target=root/'.local_agent'/('archive-replay78-late-'+uuid.uuid4().hex);target.mkdir();start=time.perf_counter();checks=0;paths=set()
for name,digest in m['archives'].items():
 p=root/'results/dev_aux'/name;h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 assert h.hexdigest()==digest
 with zipfile.ZipFile(p)as z:
  manifest=json.loads(z.read(next(n for n in z.namelist()if n.startswith('MANIFEST'))));files=manifest['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
  for n,r in files.items():
   dest=target/n;assert dest.resolve().is_relative_to(target.resolve())and not Path(n).is_absolute();dest.parent.mkdir(parents=True,exist_ok=True);old=hashlib.sha256(dest.read_bytes()).hexdigest()if dest.exists()else None
   if old!=r['sha256']:
    if old is not None:assert manifest.get('overrides',{}).get(n)==old
    h=hashlib.sha256()
    with z.open(n)as src,dest.open('wb')as dst:
     for b in iter(lambda:src.read(1024*1024),b''):h.update(b);dst.write(b)
    assert h.hexdigest()==r['sha256']
   checks+=1;paths.add(n)
 print(name+' restored/verified',flush=True)
site=str(target/'.venv/Lib/site-packages');prefix='import sys;from pathlib import Path;sys.path.insert(0,'+repr(site)+');import generic_chess;assert Path(generic_chess.__file__).resolve().is_relative_to(Path.cwd());'
numeric=prefix+'sys.path.append('+repr(str(root/'.venv/Lib/site-packages'))+');import numpy;assert numpy.__version__=="1.26.4";'
safety='from results.dev_aux.task2153.stop_evidence import EvidenceStopReader;actual_reader=EvidenceStopReader(Path('+repr(str(root))+'));'
env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
tests=['results/dev_aux/task2148/test_normal.py','results/dev_aux/task2210/test_paid_graph_player.py','results/dev_aux/task2226/test_height_adapter.py']
stages=[('related_tests',prefix+'import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());raise SystemExit(pytest.main('+repr(tests+['-q','--basetemp=.tests78','--junitxml=.tests78.xml','--tb=short'])+'))')]
for task,module,call in [(2263,'audit_learning','run(2261)'),(2272,'consume','run()'),(2275,'consume','run()'),(2276,'consume','run()'),(2280,'consume','run()')]:
 stages.append((f'closed{task}',numeric+safety+f'from results.dev_aux.task{task} import {module} as audit;audit.EvidenceStopReader=lambda ignored:actual_reader;audit.OUT=Path(".closed{task}");audit.OUT.mkdir();audit.{call}'))
for task in(2262,2265,2268,2273):
 stages.append((f'paid{task}',numeric+safety+f'from results.dev_aux.task2274 import consume as audit;audit.EvidenceStopReader=lambda ignored:actual_reader;audit.OUT=Path(".paid{task}");audit.OUT.mkdir();audit.run({task})'))
stages.append(('DFS_qualification',numeric+safety+'from results.dev_aux.task2269 import qualify;qualify.EvidenceStopReader=lambda ignored:actual_reader;qualify.OUT=Path(".DFSqualification78");qualify.OUT.mkdir();qualify.run()'))
stages.append(('TRAIN_selector_sensitivity',numeric+'from results.dev_aux.task2277 import sensitivity;sensitivity.OUT=Path(".sensitivity78");sensitivity.OUT.mkdir();sensitivity.run()'))
stages.append(('NN_direct_priority_qualification',numeric+safety+'from results.dev_aux.task2282 import qualify;qualify.EvidenceStopReader=lambda ignored:actual_reader;qualify.OUT=Path(".NNqualification78");qualify.OUT.mkdir();import shutil;shutil.copyfile("results/dev_aux/task2282/inputs.json",qualify.OUT/"inputs.json");qualify.run()'))
stages.append(('NN_direct_priority_journal',numeric+safety+'from results.dev_aux.task2282 import consume as audit;audit.EvidenceStopReader=lambda ignored:actual_reader;audit.OUT=Path(".NNjournal78");audit.OUT.mkdir();audit.run()'))
for name,code in stages:
 with(target/(name+'.log')).open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=700)
 if r.returncode:raise RuntimeError(name+' failed; exactprivate log '+str(target))
 print(name+' PASS',flush=True)
x=ET.parse(target/'.tests78.xml').getroot();ss=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in ss)for k in('tests','errors','failures','skipped')}
result=dict(status='PASS_FRESH_TWENTY_ARCHIVE_NEW78_AND_LATE_NN_SOURCE_REPLAY',payload_checks=checks,unique_paths=len(paths),tests=counts,seconds=time.perf_counter()-start,stages=[n for n,c in stages],scope='FreshignoredUUID/exact20ZIPs/declaredAST-equivalentcurrentbytepin overlays;Python-S/emptyPYTHONPATH/freshmodulepathassertions. ALLnewclosed768learning/256validation/64fixedfoe2x2/189paidqueries/39historyproofs/192firstdifferences consumed, related23regressions and4actualDFSfixtureproofs+16boundarycontrols reexecuted asqualificationtests only. LateNN512plannedjournal/UNKNOWN plus128fullD3normalqualitychecks and283968strictguiderankchecks replayed; qualificationsnotstatisticaltraining. No frozenstudy/census/training/fullgameproducer/refit/capreset. Old18/19replayhistoricalreceipts notrerun orclaimednew. HostWindows/Python/NumPy1.26.4qualifiedruntime;purepytest/chessbundled. Scientificinputsarchive-only; realhoststopreaderinjection/no fakeflags/crosswrites/network/Slack.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(result))
