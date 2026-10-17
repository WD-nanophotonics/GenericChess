"""Fresh exact-source tests and independently coded CLOSED-data audit, no new fitness."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def run():
 start=time.perf_counter();archive=OUT/'DELTA_REPRO_20261017_88.zip';fresh=ROOT/'.local_agent'/('method88-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_88.json'))
  for name in z.namelist():assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256']
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py'];site=str(ROOT/'.venv/Lib/site-packages')
 code="import sys,pathlib; sys.path[:0]=["+repr(str(fresh))+','+repr(site)+"]; import results.dev_aux.task2504.search as search; assert pathlib.Path(search.__file__).resolve().is_relative_to(pathlib.Path.cwd()); import pytest; assert pytest.main(['-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml',"+','.join(repr(t)for t in targets)+"])==0; from results.dev_aux.task2514.training_audit import training; training(); from results.dev_aux.task2514.evaluation_audit import run; run('endpoint'); run('midpoint'); run('different_foe'); from results.dev_aux.task2520.calibration_audit import run as c; c(); from results.dev_aux.task2520.training_audit import training as t; t(); from results.dev_aux.task2520.evaluation_audit import run as e; e('root_control')"
 # Park exact sealed derived outputs so a missing recomputation cannot compare
 # an extracted original to itself. All paths stay inside this new UUID tree.
 for task,names in(('task2514',('training-audit.json','endpoint-audit.json','midpoint-audit.json','different_foe-audit.json')),('task2520',('calibration-audit.json','training-audit.json','root_control-audit.json'))):
  for name in names:
   target=fresh/'results/dev_aux'/task/name;assert target.resolve().is_relative_to(fresh.resolve());target.rename(target.with_name(name+'.sealed-original'));assert not target.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 with(ROOT/'.local_agent/method88-fresh.log').open('w')as f:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 assert r.returncode==0,'Inspectprivate method88-fresh.log';legal=0
 for name in('training-audit.json','endpoint-audit.json','midpoint-audit.json','different_foe-audit.json'):
  a=json.loads((fresh/'results/dev_aux/task2514'/name).read_text());b=json.loads((OUT/'task2514'/name).read_text());a.pop('audit_seconds');b.pop('audit_seconds');assert a==b,name
  counts=a['counts'];legal+=counts.get('prefix_plies',0)+counts.get('training_plies',0)+counts.get('legal_prefix_plies',0)+counts.get('legal_play_plies',0)
 for name in('calibration-audit.json','training-audit.json','root_control-audit.json'):
  a=json.loads((fresh/'results/dev_aux/task2520'/name).read_text());b=json.loads((OUT/'task2520'/name).read_text());a.pop('audit_seconds',None);b.pop('audit_seconds',None);assert a==b,name
  counts=a.get('counts',{});legal+=a.get('legal_prefix_plies',0)+counts.get('prefix_plies',0)+counts.get('training_plies',0)+counts.get('legal_prefix_plies',0)+counts.get('legal_play_plies',0)
 record=dict(status='PASS_FRESH_EXACT_SOURCE_TESTS_ALL_UPDATES_AND_ACTUAL_GAME_RECORDS',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),tests=36,legal_plies=legal,seconds=time.perf_counter()-start,scope='FreshignoredUUID/Python-S/emptyPYTHONPATH/extractedsourceasserted, explicitexistingchess+pytestdeps. Sealedderivedoutputsparkedbeforecompute; independentlycodedallTree/Rootgradients/forwardTD/calibration/allactualrecord/queryaudits regeneratedandequalexceptauditwalltime. No newproducer/training/fitness/alloldconsumerrerun/externalengine.');(OUT/'task2515/fresh-receipt.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':run()
