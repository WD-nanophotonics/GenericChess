"""Fresh exact source/data replay of all92 audits and38 controls."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def run():
 start=time.perf_counter();archive=OUT/'DELTA_REPRO_20261017_92.zip';fresh=ROOT/'.local_agent'/('method92-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_92.json'))
  for name in z.namelist():
   assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():
  h=hashlib.sha256()
  with(fresh/name).open('rb')as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  assert h.hexdigest()==r['sha256'],name
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py']
 outputs=['training-audit.json','evaluation-audit.json','diagnostics.json','roots.json','search-verification.json','information.json','early-credit.json','training-audit-first-rule.json','interaction.json','unchanged.json']
 outputs=['task2541/'+name for name in outputs]+['task2544/audit.json']
 for name in outputs:
  t=fresh/'results/dev_aux'/name;t.rename(t.with_name(t.name+'.sealed-original'));assert not t.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 code="import sys,pathlib;sys.path[:0]="+repr([str(fresh),site])+";import results.dev_aux.task2504.search as source;assert pathlib.Path(source.__file__).resolve().is_relative_to(pathlib.Path.cwd());import pytest;assert pytest.main(['-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml']+"+repr(targets)+")==0"
 for mod in('training_audit','evaluation_audit','diagnostics','roots','information','early_credit','interaction','unchanged'):code+=';from results.dev_aux.task2541.'+mod+' import run as again;again()'
 code+=';from results.dev_aux.task2541.training_audit import run as early;early(prefix_rule=271001)'
 code+=';from results.dev_aux.task2544.audit import run as followup;followup()'
 code+=';from results.dev_aux.task2541.search_verification import run as sv;sv(stop_root='+repr(str(ROOT))+')'
 with(ROOT/'.local_agent/method92-fresh.log').open('w')as f:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0,'Inspectprivate method92-fresh.log';counts={};legal=0
 for name in outputs:
  a=json.loads((fresh/'results/dev_aux'/name).read_text());b=json.loads((OUT/name).read_text())
  for k in('audit_seconds','seconds'):a.pop(k,None);b.pop(k,None)
  assert a==b,name;counts[name]=a['status'];cs=a.get('counts',{});legal+=sum(cs.get(k,0)for k in('prefix_plies','training_plies','legal_prefix_plies','legal_play_plies'))
 record=dict(status='PASS_FRESH38_AND_11_REGENERATED_AUDITS',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),tests=38,derived=counts,legal_plies=legal,fresh_unpruned_nodes=json.loads((fresh/'results/dev_aux/task2541/search-verification.json').read_text())['nodes'],executed_wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),seconds=time.perf_counter()-start,scope='NewignoredUUID/Python-S/emptyPYTHONPATH/extractedsourceasserted; actualsealed11outputsparkedBEFORErecompute/equalityexceptauditwalltime. Sameinstalledchess/pytestdependencies. Actualowner/PRIMARYstopsreadexplicitly, nofakecopiedflags. No newtraining/fitness/allhistoricalconsumerbatch/externalrulesengine. Logicalplycounterincludesactualfirst-ruleprefixreplayAGAIN inadditiontofullaudit; notuniquestates. Earlysigncase/additionalCorecallsnotincluded.');(OUT/'task2542/fresh-receipt.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':run()
