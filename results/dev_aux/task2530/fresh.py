"""Fresh exact source/data consumer:38controls and recomputed90audits."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def run():
 start=time.perf_counter();archive=OUT/'DELTA_REPRO_20261017_90.zip';fresh=ROOT/'.local_agent'/('method90-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_90.json'))
  for name in z.namelist():
   assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256'],name
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py']
 # Explicit2ndorder real-qDATAdependency; no currentcheckout receipt fallthrough.
 hasfoe=(fresh/'results/dev_aux/task2531/result.json').exists();outputs=['training-audit.json','evaluation-audit.json','learning-diagnostics.json','search-verification.json','root-overlap.json','resource-diagnostics.json','free-model-preflight.json']+(['foe-audit.json','foe-shift.json']if hasfoe else[])
 for name in outputs:
  t=fresh/'results/dev_aux/task2529'/name;t.rename(t.with_name(name+'.sealed-original'));assert not t.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 code="import sys,pathlib;sys.path[:0]="+repr([str(fresh),site])+";import results.dev_aux.task2504.search as source;assert pathlib.Path(source.__file__).resolve().is_relative_to(pathlib.Path.cwd());import pytest;assert pytest.main(['-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml']+"+repr(targets)+")==0;from results.dev_aux.task2529.training_audit import run as t;t();from results.dev_aux.task2529.evaluation_audit import run as e;e();from results.dev_aux.task2529.diagnostics import run as d;d();from results.dev_aux.task2529.roots import run as roots;roots();from results.dev_aux.task2529.resources import run as resources;resources();from results.dev_aux.task2529.search_verification import run as v;v(stop_root="+repr(str(ROOT))+");from results.dev_aux.task2532.preflight import run as fp;fp(replay=True,stop_root="+repr(str(ROOT))+")"
 if hasfoe:code+=';from results.dev_aux.task2529.foe_audit import run as f;f();from results.dev_aux.task2529.foe_shift import run as fs;fs()'
 with(ROOT/'.local_agent/method90-fresh.log').open('w')as f:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0,'Inspectprivate method90-fresh.log';counts={};legal=0
 for name in outputs:
  a=json.loads((fresh/'results/dev_aux/task2529'/name).read_text());b=json.loads((OUT/'task2529'/name).read_text())
  for k in('audit_seconds','seconds'):a.pop(k,None);b.pop(k,None)
  assert a==b,name;counts[name]=a['status'];cs=a.get('counts',{});legal+=sum(cs.get(k,0)for k in('prefix_plies','training_plies','legal_prefix_plies','legal_play_plies'))
 record=dict(status='PASS_EXACT_FRESH38_AND_ALL_REGISTERED_RETURNED_GENERIC_CURVE_AUDITS',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),tests=38,derived=counts,legal_plies=legal,seconds=time.perf_counter()-start,scope='NewignoredUUID/Python-S/emptyPYTHONPATH/extractedsourceasserted. AllsealedderivedoutputsPARKEDbeforeRECOMPUTE; equalityexceptauditwalltimes. IndependentD2verification addsinternalnodesreportedelsewhere, no newtraining/fitness/alloldconsumerbatch/externalrulesengine. Sameinstalledchess+pytest deps; verificationexplicitlyreadsactualowner+PRIMARYstopflags viaownroot, notfakecopiedstops. No productioncode/datafallthrough.');(OUT/'task2530/fresh-receipt.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':run()
