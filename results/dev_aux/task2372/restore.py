"""Fresh26archive replay of NEW82 closed evidence, no study producer/refit."""
from pathlib import Path
import json,zipfile,hashlib,subprocess,sys,os,time,uuid,xml.etree.ElementTree as ET
root=Path.cwd();m=json.loads((root/'results/dev_aux/ARCHIVE_MANIFEST_20261017_82.json').read_text());target=root/'.local_agent'/('archive-replay82-'+uuid.uuid4().hex);target.mkdir();(target/'.local_agent').mkdir();start=time.perf_counter();checks=0;paths=set()
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
tests=['results/dev_aux/task2354/test_closure.py','results/dev_aux/task2148/test_normal.py','results/dev_aux/task2210/test_paid_graph_player.py','results/dev_aux/task2226/test_height_adapter.py','results/dev_aux/task2320/test_refutation.py']
stages=[('related_tests',prefix+'import results.dev_aux.task2153.stop_evidence as stops;OriginalStopReader=stops.EvidenceStopReader;stops.EvidenceStopReader=lambda ignored:OriginalStopReader(Path('+repr(str(root))+'));import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());raise SystemExit(pytest.main('+repr(tests+['-q','--basetemp=.tests82','--junitxml=.tests82.xml','--tb=short'])+'))')]
consumer_stages=[(2356,'qualify',None),(2359,'consume',2358),(2360,'journal',None),(2357,'select',None),(2361,'analyze',None),(2370,'resources',None),(2373,'mechanism',2358),(2374,'associate',2358),(2375,'convert',2358),(2376,'qualify',None),(2378,'associate',None)]
if(root/'results/dev_aux/task2362/started.json').exists():consumer_stages += [(2363,'consume',2362),(2364,'analyze',2362),(2365,'journal',None),(2375,'convert',2362)]
if(root/'results/dev_aux/task2366/started.json').exists():consumer_stages += [(2368,'consume',2366),(2367,'select',None),(2369,'analyze',None),(2370,'journal',None),(2373,'mechanism',2366)]
for task,module,arg in consumer_stages:
 label=f'closed{task}_{module}'+(''if arg is None else'_'+str(arg));call='audit.run()'if arg is None else'audit.run('+str(arg)+')'
 stages.append((label,numeric+safety+f'from results.dev_aux.task{task} import {module} as audit;audit.EvidenceStopReader=lambda ignored:actual_reader;audit.OUT=Path(".{label}");audit.OUT.mkdir();'+call))
for name,code in stages:
 with(target/(name+'.log')).open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=700)
 if r.returncode:raise RuntimeError(name+' failed; exactprivate log '+str(target))
 print(name+' PASS',flush=True)
x=ET.parse(target/'.tests82.xml').getroot();ss=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in ss)for k in('tests','errors','failures','skipped')}
result=dict(status='PASS_FRESH_TWENTY_SIX_ARCHIVE_NEW82_SOURCE_REPLAY',payload_checks=checks,unique_paths=len(paths),tests=counts,seconds=time.perf_counter()-start,stages=[n for n,c in stages],scope='FreshignoredUUID/exact26ZIPs/raw-source-bytepin overlays/Python-S/emptyPYTHONPATH/restoredmoduleassertions/qualifiedhostNumPy1.26.4 and actualhoststopreader.39relatedtests incl actualobservedfaultclosure controls; NEW82complete-order TRAINmatrix/reuse/proof-cursors/committedjournals/strictselection/internalbounds/resources and executedconditionalvalidation OR followup consumers. No producer/refitqueries/referencecensus/oldcapreset. Sameimplementationreplay, notexternalengine; no fakeflags orPRIMARYwrite.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(result))
