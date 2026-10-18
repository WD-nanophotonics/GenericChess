"""Actual new ignored extraction, source assertions and regenerated ALL96 audits."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();O=ROOT/'results/dev_aux/task2567'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261019_96.zip';fresh=ROOT/'.local_agent'/('method96-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  m=json.loads(z.read('MANIFEST_20261019_96.json'))
  for n in z.namelist():assert(fresh/n).resolve().is_relative_to(fresh.resolve());z.extract(n,fresh)
 for n,r in m['files'].items():assert hashlib.sha256((fresh/n).read_bytes()).hexdigest()==r['sha256'],n
 derived=[]
 for domain in('chess','generic'):
  for name in('audit.json','signals.json','witness-queries.json','unpruned.json','deployment-audit.json','summary.json','exposure.json','credit-cancellation.json','shadow-rate-curve.json'):derived.append('task2565/'+domain+'/'+name)
 derived.append('task2565/chess-curve/deployment-audit.json');derived.append('task2565/design-costs.json');derived.append('task2565/receipt-coherence.json')
 for n in derived:
  p=fresh/'results/dev_aux'/n;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TEMP=str(fresh/'.tmp'),TMP=str(fresh/'.tmp'))
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2565/test_regimes.py','results/dev_aux/task2566/test_tc.py','results/dev_aux/task2566/test_prediction_quality.py']
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import generic_chess.session.session as core;import results.dev_aux.task2565.train as train;import results.dev_aux.task2565.audit as audit;import results.dev_aux.task2565.verify as verify;import results.dev_aux.task2492.episode as episode;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(core,train,audit,verify,episode));import pytest;counter=type('ActualCount',(object,),{'pytest_sessionfinish':lambda self,session,exitstatus:setattr(self,'total',session.testscollected)})();assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini']+"+repr(targets)+",plugins=[counter])==0;assert counter.total==44"
 for domain in('chess','generic'):
  d='results/dev_aux/task2565/'+domain;code+=';audit.run('+repr(d)+',stop_root='+repr(str(ROOT))+');verify.unpruned('+repr(d)+',stop_root='+repr(str(ROOT))+');verify.deployment('+repr(d)+',stop_root='+repr(str(ROOT))+')'
  code+=';from results.dev_aux.task2565.credits import run as credits;credits('+repr(d)+')'
  code+=';from results.dev_aux.task2565.summary import run as summary;summary('+repr(d)+');from results.dev_aux.task2565.exposure import run as exposure;exposure('+repr(d)+')'
 code+=';verify.deployment("results/dev_aux/task2565/chess-curve",stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2565.design import run as design;design()'
 code+=';from results.dev_aux.task2565.receipt_coherence import run as coherent;coherent()'
 with(O/'fresh-output.log').open('wb')as f:r=subprocess.run([sys.executable,'-B','-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Actualfreshfailed, fulloutput retained'
 def stable(v):return{k:x for k,x in v.items()if k not in('seconds','audit_seconds')}if isinstance(v,dict)else v
 results={}
 for n in derived:
  p=fresh/'results/dev_aux'/n;a=json.loads(p.read_text());b=json.loads(p.with_name(p.name+'.sealed-original').read_text());assert stable(a)==stable(b),n;results[n]=a.get('status')if isinstance(a,dict)else'EXACT_LIST'
 receipt=dict(status='PASS_ACTUAL_FRESH44_AND21_REGENERATIONS',tests=44,derived=results,payloads=len(m['files']),archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),seconds=time.perf_counter()-began,wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Actual newextraction/rawbytepins/sourcepaths/44tests;21outputs parked BEFOREregenerate and matched excludingONLYtop-level auditseconds. SameCore/sample notindependentexternalengine/allrulesproof; no newtraining/fitness/oldcap extension. Actualownedstoproot passed, nofakeflags.')
 (O/'fresh-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':run()
