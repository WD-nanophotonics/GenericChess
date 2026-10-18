"""Fresh exact94 consumer: existing43 tests, regenerated new audits, no new fitness."""
from pathlib import Path
import json,hashlib,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();O=ROOT/'results/dev_aux/task2554'
def run():
 began=time.perf_counter();archive=ROOT/'results/dev_aux/DELTA_REPRO_20261019_94.zip';fresh=ROOT/'.local_agent'/('method94-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261019_94.json'))
  for name in z.namelist():
   assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():
  h=hashlib.sha256()
  with(fresh/name).open('rb')as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert h.hexdigest()==r['sha256'],name
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py','results/dev_aux/task2546/test_learning.py']
 derived=['task2553/audit.json','task2553/unpruned.json','task2553/roots-2552.json','task2553/roots-2556.json','task2557/training-audit.json','task2557/training-audit-first-rule.json','task2557/unpruned.json','task2557/deployment.json','task2557/signals.json','task2557/costs.json','task2557/signals-D2.json','task2557/signal-baseline-check.json','task2557/design-binding.json']
 for name in derived:
  p=fresh/'results/dev_aux'/name;p.rename(p.with_name(p.name+'.sealed-original'));assert not p.exists()
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');(fresh/'.tmp').mkdir();site=str(ROOT/'.venv/Lib/site-packages');env=dict(os.environ);env.update(PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',TEMP=str(fresh/'.tmp'),TMP=str(fresh/'.tmp'))
 code='import sys,pathlib;sys.path[:0]='+repr([str(fresh),site])+";import generic_chess.session.session as core;import results.dev_aux.task2552.evaluate as a;import results.dev_aux.task2555.run as b;import results.dev_aux.task2504.search as search;import results.dev_aux.task2492.learning as learner;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd())for m in(core,a,b,search,learner));import pytest;counter=type('ActualCount',(object,),{'pytest_sessionfinish':lambda self,session,exitstatus:setattr(self,'total',session.testscollected)})();assert pytest.main(['--basetemp=.pytest-tmp','-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini']+"+repr(targets)+" ,plugins=[counter])==0;assert counter.total==43"
 code+=';from results.dev_aux.task2553.audit import run as audit;audit(stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2553.unpruned import run as searchcheck;searchcheck(stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2553.roots import run as roots;roots()'
 code+=';from results.dev_aux.task2557.training_audit import run as train;train(stop_root='+repr(str(ROOT))+');train(prefix_rule=271001,stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2557.unpruned import run as trainsearch;trainsearch(stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2557.deployment_audit import run as dep;dep(stop_root='+repr(str(ROOT))+')'
 code+=';from results.dev_aux.task2557.signals import run as signals;signals();from results.dev_aux.task2557.baseline_check import run as basecheck;basecheck();from results.dev_aux.task2557.design_binding import run as design;design();from results.dev_aux.task2557.costs import run as costs;costs()'
 with(O/'fresh-output.log').open('wb')as f:r=subprocess.run([sys.executable,'-B','-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,'Actual fresh processfailed; log retained, no successimputation'
 def stable(v):return{k:x for k,x in v.items()if k not in('seconds','audit_seconds')}
 statuses={};plies=0
 for name in derived:
  p=fresh/'results/dev_aux'/name;x=json.loads(p.read_text());y=json.loads(p.with_name(p.name+'.sealed-original').read_text());assert stable(x)==stable(y),name;statuses[name]=x.get('status');c=x.get('counts',{});plies+=sum(c.get(k,0)for k in('prefix_plies','played_plies','training_plies'))
 result=dict(status='PASS_FRESH43_AND_13_REGENERATED_AUDITS',tests=43,derived=statuses,archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),logical_replay_plies=plies,unpruned_nodes=sum(json.loads((fresh/'results/dev_aux'/n).read_text())['nodes']for n in['task2553/unpruned.json','task2557/unpruned.json']),seconds=time.perf_counter()-began,executed_wrapper_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Actual new ignored extraction/allbytepins/Python-S/emptyPYTHONPATH/sourceassertions/43existingchecks; ALL13derivedoutputs parked BEFOREregeneration, exactsemanticmatches exceptauditownelapsedtime. Full newhistories+first-ruleAGAIN logical counts, notuniqueallCorecalls. Existing93TRAINparsed for signals, not re-executed or independently allrule-replayed here. Unpruned actual queries sampled prospectively; not allsearches/allrules/externalengine proof. No newtraining/fitness/oldpartialcap continuation; currentactualstopowner passed, nofakeflagtrees.')
 (O/'fresh-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
