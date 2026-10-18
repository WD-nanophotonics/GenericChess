"""Actual fresh extraction, source assertions, tests, and parked audit regeneration."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task2573'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261019_98.zip';fresh=ROOT/'.local_agent'/('chess98-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261019_98.json'))
  for name in z.namelist():assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256'],name
 derived=[('task2571',n)for n in('binding-audit.json','deployment-audit.json','summary.json','trajectory-divergence.json','loss-diagnostics.json')]+[('task2572',n)for n in('deployment-audit.json','summary.json','trajectory-divergence.json','absolute-wld.json')]+[('task2574',n)for n in('audit.json','signals.json','witness-queries.json')]+[('task2575',n)for n in('result.json','deployment-audit.json','summary.json')]
 for task,name in derived:
  p=fresh/'results/dev_aux'/task/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]'+chr(10)+'addopts='+chr(10));(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TEMP=str(fresh/'.tmp'),TMP=str(fresh/'.tmp'))
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2566/test_tc.py','results/dev_aux/task2568/test_training.py','results/dev_aux/task2571/test_diagnostics.py']
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import results.dev_aux.task2571.analyze as a;import results.dev_aux.task2572.analyze as b;import results.dev_aux.task2568.verify as v;import results.dev_aux.task2571.trajectory as tr;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(a,b,v,tr));import pytest;counter=type('ActualCount',(object,),{'pytest_sessionfinish':lambda self,session,exitstatus:setattr(self,'total',session.testscollected)})();assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','-p','no:cacheprovider']+"+repr(targets)+",plugins=[counter])==0;assert counter.total==39"
 code+=';a.bindings();v.deployment("results/dev_aux/task2571",stop_root='+repr(str(ROOT))+');a.summarize();from results.dev_aux.task2571.loss import run as loss;loss();tr.run("results/dev_aux/task2571");v.deployment("results/dev_aux/task2572",stop_root='+repr(str(ROOT))+');b.run();from results.dev_aux.task2572.absolute import run as absolute;absolute();tr.run("results/dev_aux/task2572")'
 code+=';import results.dev_aux.task2574.audit as teach;import results.dev_aux.task2574.bind_eval as bind;import results.dev_aux.task2574.analyze_eval as ts;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(teach,bind,ts));teach.run("results/dev_aux/task2574",stop_root='+repr(str(ROOT))+');bind.run();v.deployment("results/dev_aux/task2575",stop_root='+repr(str(ROOT))+');ts.run()'
 with(OUT/'fresh-output.log').open('wb')as f:r=subprocess.run([sys.executable,'-B','-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Actualfreshfailed, fulloutputretained'
 def stable(x):return{k:v for k,v in x.items()if k not in('seconds','audit_seconds')}if isinstance(x,dict)else x
 checks={}
 for task,name in derived:
  p=fresh/'results/dev_aux'/task/name;assert stable(json.loads(p.read_text()))==stable(json.loads(p.with_name(p.name+'.sealed-original').read_text())),(task,name);checks[task+'/'+name]='MATCH_EXCEPT_AUDIT_SECONDS'
 r=dict(status='PASS_ACTUAL_FRESH39_AND15_REGENERATIONS',tests=39,derived=checks,payloads=len(manifest['files']),archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),seconds=time.perf_counter()-began,wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='ActualnewUUIDextraction, exactpayloadhashes andsourcepathassertions; outputs parkedbefore39tests/15regenerations. Actualownstoproot; no fakeflags/newTRAIN/fitnessrerun/oldcaprefill. Samechessauthority, notexternalengine/allruleproof.')
 (OUT/'fresh-receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
