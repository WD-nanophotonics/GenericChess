"""Fresh31archive replay of NEW86 closed evidence, no study producer/refit."""
from pathlib import Path
import json,zipfile,hashlib,subprocess,sys,os,time,uuid,xml.etree.ElementTree as ET
root=Path.cwd();m=json.loads((root/'results/dev_aux/ARCHIVE_MANIFEST_20261017_86.json').read_text());target=root/'.local_agent'/('archive-replay86-'+uuid.uuid4().hex);target.mkdir();(target/'.local_agent').mkdir();(target/'pytest-replay.ini').write_text('[pytest]\naddopts =\n',encoding='utf-8');start=time.perf_counter();checks=0;paths=set()
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
safety='from results.dev_aux.task2392.reader import SharedDeleteStopReader;actual_reader=SharedDeleteStopReader(Path('+repr(str(root))+'));'
env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
tests=['results/dev_aux/task2401/test_closure.py','results/dev_aux/task2379/test_reader.py','results/dev_aux/task2382/test_selector.py','results/dev_aux/task2384/test_exit.py','results/dev_aux/task2392/test_sharing.py','results/dev_aux/task2392/test_contract.py','results/dev_aux/task2354/test_closure.py','results/dev_aux/task2148/test_normal.py','results/dev_aux/task2210/test_paid_graph_player.py','results/dev_aux/task2226/test_height_adapter.py','results/dev_aux/task2320/test_refutation.py','results/dev_aux/task2441/test_strict_depth.py','results/dev_aux/task2479/test_strict_depth.py']
stages=[('related_tests',prefix+'import results.dev_aux.task2379.reader;import results.dev_aux.task2392.reader as native;import results.dev_aux.task2354.pilot as legacy;import results.dev_aux.task2401.pilot as newpilot;import results.dev_aux.task2401.test_closure as newtest;import results.dev_aux.task2441.pilot as strictpilot;import results.dev_aux.task2479.pilot as rolepilot;import results.dev_aux.task2153.stop_evidence as stops;OriginalStopReader=native.SharedDeleteStopReader;stops.EvidenceStopReader=lambda ignored:OriginalStopReader(Path('+repr(str(root))+'));legacy.EvidenceStopReader=stops.EvidenceStopReader;newpilot.EvidenceStopReader=stops.EvidenceStopReader;newtest.EvidenceStopReader=stops.EvidenceStopReader;strictpilot.EvidenceStopReader=stops.EvidenceStopReader;rolepilot.EvidenceStopReader=stops.EvidenceStopReader;import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());raise SystemExit(pytest.main('+repr(tests+['-q','--import-mode=importlib','-c','pytest-replay.ini','--rootdir=.','--confcutdir=.','--basetemp=.tests86','--junitxml=.tests86.xml','--tb=short'])+'))')]
consumer_stages=[(2468, 'consume', None, 'SharedDeleteStopReader'), (2470, 'consume', None, 'SharedDeleteStopReader'), (2477, 'consume', None, 'SharedDeleteStopReader'), (2478, 'consume', None, 'SharedDeleteStopReader'), (2475, 'audit', None, 'SharedDeleteStopReader'), (2476, 'consume', 2474, 'EvidenceStopReader'), (2476, 'journal', 2474, 'EvidenceStopReader'), (2483, 'consume', 2479, 'EvidenceStopReader'), (2483, 'journal', 2479, 'EvidenceStopReader'), (2483, 'consume', 2481, 'EvidenceStopReader'), (2483, 'journal', 2481, 'EvidenceStopReader'), (2484, 'audit', None, None), (2485, 'select', None, None), (2486, 'analyze', None, None), (2487, 'audit', None, 'SharedDeleteStopReader'), (2491, 'audit', None, 'SharedDeleteStopReader')]
for task,module,arg,reader_name in consumer_stages:
 label=f'closed{task}_{module}'+(''if arg is None else'_'+str(arg));call='audit.run()'if arg is None else'audit.run('+str(arg)+')';patch=''if reader_name is None else'audit.'+reader_name+'=lambda ignored:actual_reader;'
 stages.append((label,numeric+safety+f'from results.dev_aux.task{task} import {module} as audit;'+patch+f'audit.OUT=Path(".{label}");audit.OUT.mkdir();actual_reader();'+call+';actual_reader()'))

for name,code in stages:
 with(target/(name+'.log')).open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=700)
 if r.returncode:raise RuntimeError(name+' failed; exactprivate log '+str(target))
 print(name+' PASS',flush=True)
x=ET.parse(target/'.tests86.xml').getroot();ss=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in ss)for k in('tests','errors','failures','skipped')}
result=dict(status='PASS_FRESH_THIRTY_ONE_ARCHIVE_86_SOURCE_REPLAY',payload_checks=checks,unique_paths=len(paths),tests=counts,seconds=time.perf_counter()-start,stages=[n for n,c in stages],scope='FreshignoredUUID/exact31ZIPs/rawsource overlays/Python-S/emptyPYTHONPATH/restoredsourceassertions/qualifiedhostNumPy1.26.4/Windowsfreshhoststopauthority.88relatedtests and16NEWclosedconsumers; ALLfourcompleteD3/D5trees andactualrole-D4-D3game/phase/cursor/journal/selection/provenance/corpus/cooptimality audits. Earlier30archive-replayreceipts remainhistorical, notalloldconsumersrerunundernewrawsourceoverlays. No producer/newgame/newfitness/query/censusrerun/oldcapextension; exactlargeD5trees insidecapsule. Isolatedpytestconfig/importlib andsourceclosure; sameCore/verifier notexternalengine.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(result))
