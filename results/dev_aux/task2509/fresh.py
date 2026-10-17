"""Fresh exact capsule replay, no producer/fitness/price fitting."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def run():
 start=time.perf_counter();archive=OUT/'DELTA_REPRO_20261017_87.zip';fresh=ROOT/'.local_agent'/('td87-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  m=json.loads(z.read('MANIFEST_20261017_87.json'))
  for name in z.namelist():assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for n,r in m['files'].items():assert hashlib.sha256((fresh/n).read_bytes()).hexdigest()==r['sha256']
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py'];site=str(ROOT/'.venv/Lib/site-packages')
 code="import sys,pathlib; sys.path[:0]=["+repr(str(fresh))+','+repr(site)+"]; import results.dev_aux.task2504.search as s; assert pathlib.Path(s.__file__).resolve().is_relative_to(pathlib.Path.cwd()); import pytest; rc=pytest.main(['-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml',"+','.join(repr(t)for t in targets)+"]); assert rc==0; from results.dev_aux.task2508.training_audit import run; run(); from results.dev_aux.task2508.evaluation_audit import run as e; e(2507); e(2510); from results.dev_aux.task2508.credit_diagnostics import run as d; d(); from results.dev_aux.task2508.behavior_audit import run as b; b()"
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 with(ROOT/'.local_agent/td87-fresh.log').open('w')as f:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 assert r.returncode==0,'Inspect private td87-fresh.log'
 for n in('training-audit.json','evaluation-audit.json','curve-evaluation-audit.json','credit-diagnostics.json','behavior-audit.json'):assert json.loads((fresh/'results/dev_aux/task2508'/n).read_text())==json.loads((OUT/'task2508'/n).read_text()),n
 t=json.loads((OUT/'task2508/training-audit.json').read_text());a=json.loads((OUT/'task2508/evaluation-audit.json').read_text());b=json.loads((OUT/'task2508/curve-evaluation-audit.json').read_text());record=dict(status='PASS_FRESH_EXACT87_SOURCE_TESTS_AND_CLOSED_TD_GAME_REPLAY',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(m['files']),tests=32,training_episodes=t['counts']['episodes'],actual_deployment_games=a['games']+b['games'],legal_plies=t['counts']['legal_prefix_moves']+t['counts']['legal_training_moves']+a['legal_plies']+b['legal_plies'],seconds=time.perf_counter()-start,scope='NEWignoredUUIDdir/Python-S/emptyPYTHONPATH/importsourceasserted, explicitpytest/chessdependencies. ALLnewTDweightupdates forwardreconstructed andactualChessrecords replayed. No producer/fitness/old31consumer rerun, no externalrulesengine or universalstrengthclaim. Priorarchivehashesverifiedseparately.')
 (OUT/'task2509/fresh-receipt.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':run()
