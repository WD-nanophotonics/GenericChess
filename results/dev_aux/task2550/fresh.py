"""New isolated consumer:43 controls and16 genuinely regenerated93 audits."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();O=ROOT/'results/dev_aux/task2550'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261017_93.zip';fresh=ROOT/'.local_agent'/('method93-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_93.json'))
  for name in z.namelist():
   assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():
  h=hashlib.sha256()
  with(fresh/name).open('rb')as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  assert h.hexdigest()==r['sha256'],name
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py','results/dev_aux/task2546/test_learning.py']
 derived=['task2545/recheck.json']+['task2548/'+n for n in('training-audit.json','training-audit-first-rule.json','evaluation-audit.json','evaluation-D3-audit.json','diagnostics.json','roots.json','roots-D3.json','information.json','search-verification.json','search-verification-first-rule.json','spans.json','orders.json','loss-verification.json','unchanged.json','unchanged-D3.json')]
 for name in derived:
  p=fresh/'results/dev_aux'/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['TEMP']=str(fresh/'.tmp');env['TMP']=str(fresh/'.tmp')
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import results.dev_aux.task2546.run as source;assert pathlib.Path(source.__file__).resolve().is_relative_to(pathlib.Path.cwd());import generic_chess.session.session as core;import results.dev_aux.task2504.search as searchsource;import results.dev_aux.task2492.learning as learnersource;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(source,core,searchsource,learnersource));import pytest;assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml']+"+repr(targets)+")==0"
 code+=';from results.dev_aux.task2545.recheck import run as role;role(stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2548.training_audit import run as train;train(stop_root='+repr(str(ROOT))+');train(prefix_rule=271001,stop_root='+repr(str(ROOT))+')'
 for mod in('evaluation_audit','evaluation_D3_audit','diagnostics','roots','roots_D3','information','spans','orders','unchanged','unchanged_D3'):code+=';from results.dev_aux.task2548.'+mod+' import run as again;again()'
 code+=';from results.dev_aux.task2548.search_verification import run as search;search(stop_root='+repr(str(ROOT))+');search(prefix_rule=271001,stop_root='+repr(str(ROOT))+');from results.dev_aux.task2548.loss_verification import run as losscheck;losscheck()'
 with(O/'fresh-output.log').open('wb')as log:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Fresh processfailed; exactlog retained; no successimputation'
 def stable(x):
  # Only the audit's own top-level elapsed timer varies; nested paid producer costs stay exact.
  return {k:v for k,v in x.items()if k not in('seconds','audit_seconds')}
 counts={};legal=0
 for name in derived:
  p=fresh/'results/dev_aux'/name;actual=json.loads(p.read_text());expected=json.loads(p.with_name(p.name+'.sealed-original').read_text());assert stable(actual)==stable(expected),name;counts[name]=actual.get('status');cc=actual.get('counts',{});legal+=sum(cc.get(k,0)for k in('prefix_plies','training_plies','legal_prefix_plies','legal_play_plies'))
 receipt=dict(status='PASS_FRESH43_AND_16_REGENERATED_AUDITS',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),tests=43,derived=counts,unavailable_controls=[n for n,s in counts.items()if s.startswith('NOT_AVAILABLE')],legal_logical_plies=legal,fresh_unpruned_nodes=sum(json.loads((fresh/'results/dev_aux/task2548'/n).read_text())['nodes']for n in('search-verification.json','search-verification-first-rule.json')),fresh_unpruned_full_nodes=json.loads((fresh/'results/dev_aux/task2548/search-verification.json').read_text())['nodes'],fresh_unpruned_first_rule_nodes=json.loads((fresh/'results/dev_aux/task2548/search-verification-first-rule.json').read_text())['nodes'],executed_wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),seconds=time.perf_counter()-began,scope='ActualnewignoredUUID/exactextraction/hashverified/Python-S/emptyPYTHONPATH/importsourceasserted. ALL16sealedoutputsparkedBEFOREeachregeneration; compareexactsemanticresults exceptaudittime. Actualown+PRIMARYstops boundexplicitROOT, nofakeflagtrees. Logicalplycountincludesfirst-ruleAGAIN/fulloriginalTRAIN+twoactualEVALpanels, notuniquestates/allCorecalls. Rolefixedtrajectoryrecheck is not all92historicalrulehistoryrerun. No newtraining/fitness/allpriorconsumers/externalrulesengine. Naturalnegativecontrols with zeroeligibleunchangedmodels return NOT_AVAILABLE, not a realizedcontrolPASS. Existingchess/pytest dependenciesonly.')
 (O/'fresh-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':run()
