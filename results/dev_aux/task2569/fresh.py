"""Actual new extraction and regenerated audits, never a training/fitness rerun."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task2569'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261019_97.zip';fresh=ROOT/'.local_agent'/('chess97-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  m=json.loads(z.read('MANIFEST_20261019_97.json'))
  for name in z.namelist():assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in m['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256'],name
 derived=['audit.json','signals.json','witness-queries.json','unpruned.json','deployment-audit.json','summary.json','terminal-profile.json','design-costs.json','credit-sources.json','conditioning.json']
 for name in derived:
  p=fresh/'results/dev_aux/task2568'/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 for name in ['deployment-audit.json','summary.json']:
  p=fresh/'results/dev_aux/task2570'/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TEMP=str(fresh/'.tmp'),TMP=str(fresh/'.tmp'))
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2566/test_tc.py','results/dev_aux/task2568/test_training.py']
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import results.dev_aux.task2568.train as train;import results.dev_aux.task2568.audit as audit;import results.dev_aux.task2568.verify as verify;import results.dev_aux.task2566.tc as tc;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(train,audit,verify,tc));import pytest;counter=type('ActualCount',(object,),{'pytest_sessionfinish':lambda self,session,exitstatus:setattr(self,'total',session.testscollected)})();assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','-p','no:cacheprovider']+"+repr(targets)+",plugins=[counter])==0;assert counter.total==33"
 d='results/dev_aux/task2568';code+=';audit.run('+repr(d)+',stop_root='+repr(str(ROOT))+');verify.unpruned('+repr(d)+',stop_root='+repr(str(ROOT))+');verify.deployment('+repr(d)+',stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2568.summary import run as summarize;summarize('+repr(d)+');from results.dev_aux.task2568.terminal_profile import run as terminal;terminal('+repr(d)+')'
 code+=';verify.deployment("results/dev_aux/task2570",stop_root='+repr(str(ROOT))+');from results.dev_aux.task2570.summary import run as transfer;transfer("results/dev_aux/task2570");from results.dev_aux.task2568.design import run as design;design();from results.dev_aux.task2568.credit_sources import run as credit;credit("results/dev_aux/task2568");from results.dev_aux.task2568.conditioning import run as conditioning;conditioning("results/dev_aux/task2568")'
 with(OUT/'fresh-output.log').open('wb')as f:r=subprocess.run([sys.executable,'-B','-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Actualfreshfailed, fulloutput retained'
 def stable(x):return{k:v for k,v in x.items()if k not in('seconds','audit_seconds')}if isinstance(x,dict)else x
 checks={}
 for name in derived:
  p=fresh/'results/dev_aux/task2568'/name;assert stable(json.loads(p.read_text()))==stable(json.loads(p.with_name(p.name+'.sealed-original').read_text())),name;checks[name]='EXACT_MATCH_EXCEPT_AUDIT_SECONDS'
 for name in ['deployment-audit.json','summary.json']:
  p=fresh/'results/dev_aux/task2570'/name;assert stable(json.loads(p.read_text()))==stable(json.loads(p.with_name(p.name+'.sealed-original').read_text())),name;checks['transfer/'+name]='EXACT_MATCH_EXCEPT_AUDIT_SECONDS'
 receipt=dict(status='PASS_ACTUAL_FRESH33_AND12_REGENERATIONS',tests=33,derived=checks,payloads=len(m['files']),archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),seconds=time.perf_counter()-began,wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Actualnewextraction, allrawbytepins andsourcepathassertions;33tests/12derivedoutputs parkedthenregenerated. Actualownedstoproot, nofakeflags; sameCore/sample notexternalengine/allrulesproof. No newtraining/fitness/oldcapextension.')
 (OUT/'fresh-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':run()
