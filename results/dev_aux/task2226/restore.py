"""Fresh exact16archive source-only replay; never rerun study producers."""
from pathlib import Path
import json,zipfile,hashlib,sys,subprocess,os,time,uuid,xml.etree.ElementTree as ET
root=Path.cwd();m=json.loads((root/'results/dev_aux/ARCHIVE_MANIFEST_20261016_76.json').read_text());target=root/'.local_agent'/('archive-replay76-'+uuid.uuid4().hex);target.mkdir();start=time.perf_counter();checks=0;paths=set()
for name,digest in m['archives'].items():
 p=root/'results/dev_aux'/name;h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 assert h.hexdigest()==digest
 with zipfile.ZipFile(p)as z:
  manifest=json.loads(z.read(next(n for n in z.namelist()if n.startswith('MANIFEST'))));files=manifest['files'];files={r['path']:r for r in files}if isinstance(files,list)else files
  for n,r in files.items():
   dest=target/n;assert dest.resolve().is_relative_to(target.resolve())and not Path(n).is_absolute();dest.parent.mkdir(parents=True,exist_ok=True)
   old=hashlib.sha256(dest.read_bytes()).hexdigest()if dest.exists()else None
   if old!=r['sha256']:
    if old is not None:assert manifest.get('overrides',{}).get(n)==old
    h=hashlib.sha256()
    with z.open(n)as src,dest.open('wb')as dst:
     for b in iter(lambda:src.read(1024*1024),b''):h.update(b);dst.write(b)
    assert h.hexdigest()==r['sha256']
   checks+=1;paths.add(n)
 print(name+' restored/verified',flush=True)
site=str(target/'.venv/Lib/site-packages');prefix="import sys;from pathlib import Path;sys.path.insert(0,"+repr(site)+");import generic_chess;assert Path(generic_chess.__file__).resolve().is_relative_to(Path.cwd());"
env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
tests=['results/dev_aux/task2126/test_draw_crossing.py','results/dev_aux/task2131/test_stop_reader.py','results/dev_aux/task2136/test_legal_fallback.py','results/dev_aux/task2139/test_receipt.py','results/dev_aux/task2142/test_semantics.py','results/dev_aux/task2145','results/dev_aux/task2148/test_normal.py','results/dev_aux/task2153/test_evidence.py','results/dev_aux/task2175/test_player.py','results/dev_aux/task2180/test_graph.py','results/dev_aux/task2189/test_frontier.py','results/dev_aux/task2191/test_semantic_graph.py','results/dev_aux/task2201/test_full_scope.py','results/dev_aux/task2203/test_incremental.py','results/dev_aux/task2210/test_paid_graph_player.py','results/dev_aux/task2226/test_height_adapter.py']
stages=[('tests',prefix+"import pytest;assert Path(pytest.__file__).resolve().is_relative_to(Path.cwd());raise SystemExit(pytest.main("+repr(tests+['-q','--basetemp=.tests76','--junitxml=.tests76.xml','--tb=short'])+"))"),('proofconsumer',prefix+"from results.dev_aux.task2215 import consume;consume.OUT=Path('.consumer76');consume.OUT.mkdir();consume.run()"),('fullhistory',prefix+"from results.dev_aux.task2219 import diagnose;diagnose.OUT=Path('.height76');diagnose.OUT.mkdir();diagnose.run()")]
numeric=prefix+"sys.path.append("+repr(str(root/'.venv/Lib/site-packages'))+");import numpy;assert numpy.__version__=='1.26.4';"
for task in(2220,2224):stages.append((f'learning{task}',numeric+f"from results.dev_aux.task2225.audit_learning import audit;import json;Path('.learning{task}.json').write_text(json.dumps(audit({task})))"))
stages.append(('resource_transfer',numeric+"from results.dev_aux.task2227 import consume;import shutil;dest=Path('.transfer76');dest.mkdir();[shutil.copyfile(consume.OUT/n,dest/n) for n in ('plan.json','completion.json','games.jsonl','moves.jsonl')];consume.OUT=dest;consume.run()"))
for task in(2217,2223):stages.append((f'completeaudit{task}',prefix+f"from results.dev_aux.task{task} import audit;from results.dev_aux.task2153.stop_evidence import EvidenceStopReader;actual_reader=EvidenceStopReader(Path({str(Path.cwd())!r}));audit.EvidenceStopReader=lambda ignored:actual_reader;import shutil;dest=Path('.completeaudit{task}');dest.mkdir();shutil.copyfile(audit.OUT/'plan.json',dest/'plan.json');audit.OUT=dest;audit.run()"))
for name,code in stages:
 with(target/(name+'.log')).open('w',encoding='utf-8')as log:r=subprocess.run([sys.executable,'-S','-c',code],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 if r.returncode:raise RuntimeError(name+' failed; exactprivate log '+str(target))
 print(name+' PASS',flush=True)
x=ET.parse(target/'.tests76.xml').getroot();ss=[x]if x.tag=='testsuite'else list(x);counts={k:sum(int(s.get(k,0))for s in ss)for k in('tests','errors','failures','skipped')}
result=dict(status='PASS_FRESH_SIXTEEN_ARCHIVE_SOURCE_ONLY_REPLAY76',payload_checks=checks,unique_paths=len(paths),tests=counts,seconds=time.perf_counter()-start,stages=[n for n,c in stages],scope='FreshignoredUUIDtree/exact16ZIPs/Python-S/emptyPYTHONPATH/modulepathassertions. Regressiontinyfixtureprovers+closedproofs/actualrecords/allBellman/rank/coverage/publichistoryaudits. NOstudyproducer/fit/newstatisticalgames/capreset. SamehostPython/OS+NumPy1.26.4externalruntime; purepytestbundled. Scientificinputsarchive-only; longclosedauditsreadREALhostown/PRIMARYstopflags viaexplicitreaderinjection, neverfakestopfiles orwritePRIMARY. NoSlack/network required.')
(target/'RESTORE_RECEIPT.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REPLAY_RECEIPT='+str(target/'RESTORE_RECEIPT.json'));print(json.dumps(result))
