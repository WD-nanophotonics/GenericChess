"""Restore13 exact reviewed archives to a fresh ignored source-only tree."""
from pathlib import Path
import json,zipfile,hashlib,sys,subprocess,os,time,uuid,xml.etree.ElementTree as ET
root=Path.cwd();manifest=json.loads((root/'results/dev_aux/ARCHIVE_MANIFEST_20261016_75.json').read_text());target=root/'.local_agent'/('archive-replay75-'+uuid.uuid4().hex);target.mkdir();start=time.perf_counter();checks=0;unique=set()
for name,digest in manifest['archives'].items():
 path=root/'results/dev_aux'/name;h=hashlib.sha256()
 with path.open('rb')as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 assert h.hexdigest()==digest
 with zipfile.ZipFile(path)as z:
  m=json.loads(z.read(next(n for n in z.namelist()if n.startswith('MANIFEST'))));files=m['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
  for n,row in files.items():
   dest=target/n;assert dest.resolve().is_relative_to(target.resolve())and not Path(n).is_absolute();dest.parent.mkdir(parents=True,exist_ok=True);old=hashlib.sha256(dest.read_bytes()).hexdigest()if dest.exists()else None
   if old!=row['sha256']:
    if old is not None:assert m.get('overrides',{}).get(n)==old,'undeclaredoverlay'
    hh=hashlib.sha256()
    with z.open(n)as src,dest.open('wb')as dst:
     for chunk in iter(lambda:src.read(1024*1024),b''):hh.update(chunk);dst.write(chunk)
    assert hh.hexdigest()==row['sha256']
   checks+=1;unique.add(n)
 print(name+' verified/restored',flush=True)
site=str(target/'.venv/Lib/site-packages');base="import sys;from pathlib import Path;sys.path.insert(0,"+repr(site)+");import generic_chess;assert Path(generic_chess.__file__).resolve().is_relative_to(Path.cwd());"
tests=['results/dev_aux/task2126/test_draw_crossing.py','results/dev_aux/task2131/test_stop_reader.py','results/dev_aux/task2136/test_legal_fallback.py','results/dev_aux/task2139/test_receipt.py','results/dev_aux/task2142/test_semantics.py','results/dev_aux/task2145','results/dev_aux/task2148/test_normal.py','results/dev_aux/task2153/test_evidence.py','results/dev_aux/task2175/test_player.py','results/dev_aux/task2180/test_graph.py','results/dev_aux/task2189/test_frontier.py','results/dev_aux/task2191/test_semantic_graph.py','results/dev_aux/task2201/test_full_scope.py','results/dev_aux/task2203/test_incremental.py'];env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
for stage,code in [('tests',base+"import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());raise SystemExit(pytest.main("+repr(tests+['-q','--basetemp=.replay_tests75_owned','--junitxml=.replay75.xml','--tb=short'])+"))"),('consumers',base+"from results.dev_aux.task2205.consume import run;run()")]:
 with(target/(stage+'.log')).open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 if r.returncode:raise RuntimeError(stage+' failed; exactprivate logpreserved at '+str(target))
 print(stage+' PASS',flush=True)
x=ET.parse(target/'.replay75.xml').getroot();suites=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in suites)for k in('tests','errors','failures','skipped')};result=dict(status='PASS_FRESH_THIRTEEN_ARCHIVE_OFFLINE_REPLAY75',archive_payload_checks=checks,unique_paths=len(unique),tests=counts,consumers=json.loads((target/'.replay_output75/summary.json').read_text()),seconds=time.perf_counter()-start,scope='FreshignoredUUIDdir/13hash-pinnedreviewedarchives/Python-S/emptyPYTHONPATH/modulepathassertions. Relevantregressions incltinyboundedfixtureprovers; closedactualrecords/certificates consumers. No studyprover/fit/gamebatch/capreset. SamehostPython/OSunbundled; oldunusedbridgeprojectionunimported; owneronlyunsavedfixturewitnesses explicitlyseparated.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(dict(status=result['status'],checks=checks,paths=len(unique),tests=counts,seconds=result['seconds'])))
