"""Fresh-source38 controls and regenerated closed-data audits; no new fitness."""
from pathlib import Path
import hashlib,json,zipfile,subprocess,sys,uuid,os,time
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux'
def run():
 start=time.perf_counter();archive=OUT/'DELTA_REPRO_20261017_89.zip';fresh=ROOT/'.local_agent'/('method89-fresh-'+uuid.uuid4().hex);fresh.mkdir()
 with zipfile.ZipFile(archive)as z:
  manifest=json.loads(z.read('MANIFEST_20261017_89.json'))
  for name in z.namelist():
   assert(fresh/name).resolve().is_relative_to(fresh.resolve());z.extract(name,fresh)
 for name,r in manifest['files'].items():assert hashlib.sha256((fresh/name).read_bytes()).hexdigest()==r['sha256'],name
 targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py'];site=str(ROOT/'.venv/Lib/site-packages');names=['training-audit.json','endpoint-audit.json','different_foe-audit.json','exposure-consistency.json','training-resource-diagnostics.json']
 for name in names:
  target=fresh/'results/dev_aux/task2523'/name;assert target.resolve().is_relative_to(fresh.resolve());target.rename(target.with_name(name+'.sealed-original'));assert not target.exists()
 code="import sys,pathlib; sys.path[:0]=["+repr(str(fresh))+','+repr(site)+"]; import results.dev_aux.task2504.search as search; assert pathlib.Path(search.__file__).resolve().is_relative_to(pathlib.Path.cwd()); import pytest; assert pytest.main(['-q','--import-mode=importlib','--confcutdir=.','-c','pytest.ini','--junitxml=tests.xml',"+','.join(repr(t)for t in targets)+"])==0; from results.dev_aux.task2523.training_audit import training; training(); from results.dev_aux.task2523.evaluation_audit import run; run('endpoint'); run('different_foe'); from results.dev_aux.task2523.exposure import run as e; e(); from results.dev_aux.task2523.resources import run as resources; resources()"
 generic=OUT/'task2525/result.json';generic_audit=False
 if generic.exists():
  target=fresh/'results/dev_aux/task2525/audit.json';assert target.resolve().is_relative_to(fresh.resolve());target.rename(target.with_name('audit.json.sealed-original'));assert not target.exists();code+='; from results.dev_aux.task2525.audit import run as generic_replay; generic_replay(); from results.dev_aux.task2526.audit import run as generic_fitness; generic_fitness()';evaltarget=fresh/'results/dev_aux/task2526/audit.json';evaltarget.rename(evaltarget.with_name('audit.json.sealed-original'));assert not evaltarget.exists();generic_audit=True
 (fresh/'pytest.ini').write_text('[pytest]\naddopts=\n');env=dict(os.environ);env['PYTHONPATH']='';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 with(ROOT/'.local_agent/method89-fresh.log').open('w')as f:r=subprocess.run([sys.executable,'-S','-X','utf8','-c',code],cwd=fresh,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 assert r.returncode==0,'Inspectprivate method89-fresh.log';legal=0
 for name in names:
  a=json.loads((fresh/'results/dev_aux/task2523'/name).read_text());b=json.loads((OUT/'task2523'/name).read_text());a.pop('audit_seconds',None);b.pop('audit_seconds',None);assert a==b,name
  counts=a.get('counts',{});
  if isinstance(counts,dict):legal+=sum(counts.get(k,0)for k in('prefix_plies','training_plies','legal_prefix_plies','legal_play_plies'))
 if generic_audit:
  a=json.loads((fresh/'results/dev_aux/task2525/audit.json').read_text());b=json.loads((OUT/'task2525/audit.json').read_text());a.pop('audit_seconds');b.pop('audit_seconds');assert a==b,'Generic audit';legal+=a['counts'].get('prefix_plies',0)+a['counts'].get('training_plies',0)
 if generic_audit:
  a=json.loads((fresh/'results/dev_aux/task2526/audit.json').read_text());b=json.loads((OUT/'task2526/audit.json').read_text());a.pop('audit_seconds');b.pop('audit_seconds');assert a==b,'Generic fitness audit';legal+=a['counts'].get('legal_prefix_plies',0)+a['counts'].get('legal_play_plies',0)
 record=dict(status='PASS_FRESH_EXACT_SOURCE38_AND_REGENERATED_ALL_TD_AND_GAME_AUDITS',archive=archive.name,archive_sha=hashlib.sha256(archive.read_bytes()).hexdigest(),payloads=len(manifest['files']),generic_audit=generic_audit,tests=38,legal_plies=legal,seconds=time.perf_counter()-start,scope='NewignoredUUID/Python-S/emptyPYTHONPATH/extractedsourceasserted; sameinstalledchess+pytest externaldeps. Allsealedderivedoutputsparkedbeforecompute and REGENERATED equal exceptauditwalltime. Includesexplicitoldreal-qDATAfixture. No newtrain/fitness/alloldconsumerrerun/externalrulesengine.');(OUT/'task2524/fresh-receipt.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
if __name__=='__main__':run()
