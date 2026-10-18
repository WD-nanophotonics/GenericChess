"""Actual fresh extraction, source assertions, tests, and parked audit regeneration."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task2578'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261019_99.zip';fresh=ROOT/'.local_agent'/('chess99-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261019_99.json'))
  for name in z.namelist():assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256'],name
 derived=[('task2576',n)for n in('audit.json','signals.json','witness-queries.json','information.json','training-curves.json','first-targets.json')]+[('task2577',n)for n in('result.json','deployment-audit.json','summary.json','trajectory-divergence.json','terminal-ledger.json')]+[('task2579',n)for n in('result.json','deployment-audit.json','summary.json','terminal-ledger.json')]
 for task,name in derived:
  p=fresh/'results/dev_aux'/task/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]'+chr(10)+'addopts='+chr(10));(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TEMP=str(fresh/'.tmp'),TMP=str(fresh/'.tmp'))
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2568/test_training.py','results/dev_aux/task2571/test_diagnostics.py','results/dev_aux/task2577/test_context.py']
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import results.dev_aux.task2576.audit as a;import results.dev_aux.task2576.information as i;import results.dev_aux.task2577.bind as b;import results.dev_aux.task2577.analyze as s;import results.dev_aux.task2577.terminals as t;import results.dev_aux.task2568.verify as v;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(a,i,b,s,t,v));import pytest;counter=type('ActualCount',(object,),{'pytest_sessionfinish':lambda self,session,exitstatus:setattr(self,'total',session.testscollected)})();assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','-p','no:cacheprovider']+"+repr(targets)+",plugins=[counter])==0;assert counter.total==38"
 code+=';a.run("results/dev_aux/task2576",stop_root='+repr(str(ROOT))+');i.run();from results.dev_aux.task2576.first_targets import run as ft;ft();b.run();v.deployment("results/dev_aux/task2577",stop_root='+repr(str(ROOT))+');s.run();t.run();import results.dev_aux.task2579.bind as hb;import results.dev_aux.task2579.analyze as hs;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(hb,hs));hb.run();v.deployment("results/dev_aux/task2579",stop_root='+repr(str(ROOT))+');hs.run();t.run("results/dev_aux/task2579")'
 with(OUT/'fresh-output.log').open('wb')as f:r=subprocess.run([sys.executable,'-B','-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Actualfreshfailed, fulloutputretained'
 def stable(x):return{k:v for k,v in x.items()if k not in('seconds','audit_seconds')}if isinstance(x,dict)else x
 checks={}
 for task,name in derived:
  p=fresh/'results/dev_aux'/task/name;assert stable(json.loads(p.read_text()))==stable(json.loads(p.with_name(p.name+'.sealed-original').read_text())),(task,name);checks[task+'/'+name]='MATCH_EXCEPT_AUDIT_SECONDS'
 r=dict(status='PASS_ACTUAL_FRESH38_AND15_REGENERATIONS',tests=38,derived=checks,payloads=len(manifest['files']),archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),seconds=time.perf_counter()-began,wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='ActualnewUUIDextraction, exactpayloadhashes andsourcepathassertions; outputs parkedbefore38tests/15regenerations. Actualownstoproot; no fakeflags/newTRAIN/fitnessrerun/oldcaprefill. Samechessauthority, notexternalengine/allruleproof.')
 (OUT/'fresh-receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
