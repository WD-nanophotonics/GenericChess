from pathlib import Path
import json,hashlib,zipfile,sys,os,subprocess,time,shutil
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/movement-transfer-20261017';O=R/'docs/archive/movement_price_transfer_20261017';X=D/'fresh';X.mkdir();started=time.perf_counter()
with zipfile.ZipFile(O/'evidence.zip')as z:
 m=json.loads(z.read('manifest.json'))
 for n,e in m['files'].items():
  t=(X/n).resolve();assert t.is_relative_to(X.resolve());b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256'];t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
S=X/'source';M=S/'.local_agent/movement-transfer-20261017';M.mkdir(parents=True)
for folder in ['data/transfer','analysis/transfer']:
 for p in (X/folder).iterdir():shutil.copyfile(p,M/p.name)
A=S/'.local_agent/free-price-20261017/exact/results/dev_aux'
for p in (X/'upstream/aux91/results/dev_aux').rglob('*.json'):
 t=A/p.relative_to(X/'upstream/aux91/results/dev_aux');t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,t)
expected={};outputs=['reader-result.json','analysis.json','first-divergences.json','cohort-analysis.json','context-reuse.json','transfer-contract-audit.json','price-coordinate-audit.json','equivalent-rule-price-control.json','divergence-plan.json','divergence-inputs.json','divergence-result.json']
for n in outputs:
 p=M/n;expected[n]=json.loads(p.read_bytes());p.rename(p.with_name(n+'.sealed-original'))
py=R/'.venv/Scripts/python.exe';site=R/'.venv/Lib/site-packages';env=dict(os.environ,PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',GC_REPLAY_STOP_ROOT=str(R),ZIG=str(site/'ziglang/zig.exe'),ZIG_GLOBAL_CACHE_DIR=str(X/'zig-cache'));env.pop('NATIVE_BUILD_OUT',None);steps=[]
def poll():
 for n in ['rollout','advisor','slack']:
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('stopped')and not f.get('user_paused'),'EXPLICIT_STOP'
def execute(name,code,cap):
 poll();start=time.perf_counter();prefix='import sys,pathlib,runpy,importlib.util;sys.path[:0]='+repr([str(S),str(S/'tests'),str(S/'tests/product'),str(site)])+';'
 suffix=';assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None));'
 with(D/('fresh-'+name+'.log')).open('w',encoding='utf-8')as log:
  c=subprocess.Popen([str(py),'-S','-X','utf8','-c',prefix+code+suffix],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT)
  while c.poll()is None:
   try:poll();assert time.perf_counter()-start<cap,'FROZEN_QUALIFICATION_STAGE_CAP'
   except BaseException:c.terminate();c.wait();raise
   time.sleep(.25)
  assert c.returncode==0,(name,c.returncode)
 steps.append(dict(name=name,seconds=time.perf_counter()-start,exit_code=0));print('QUALIFIED',steps[-1],flush=True)
def run(n,cap):execute(n,"assert importlib.util.find_spec('generic_chess._native_core') is None;sys.argv=["+repr(str(M/n))+"];runpy.run_path("+repr(str(M/n)) +",run_name='__main__')",cap)
run('reader.py',920)
for n in ['analyze.py','cohort_analysis.py','context_reuse.py','transfer_contract.py','price_coordinates.py','equivalent_rules.py','prepare_divergence.py','divergence.py']:run(n,190)
execute('build',"sys.argv=["+repr(str(S/'scripts/build_native_zig.py'))+"];runpy.run_path("+repr(str(S/'scripts/build_native_zig.py'))+",run_name='__main__')",190)
execute('ten-new-controls',"import pytest;assert pytest.main(['tests/product/test_native_probe_terminal_score_band.py','-q','--basetemp',"+repr(str(X/'pytest-temp'))+",'-o','cache_dir="+str(X/'pytest-cache').replace('\\','/')+"'])==0",120)
def clean(x):
 if isinstance(x,dict):return {k:clean(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return [clean(v)for v in x]
 return x
for n,a in expected.items():assert clean(a)==clean(json.loads((M/n).read_bytes())),n
q=json.loads((O/'qualification.json').read_bytes());q.update(status='PASS_ALL_ELEVEN_EXTRACTED_SOURCE_OUTPUTS_AND_NATIVE_FIX',payload_hashes=len(m['files']),own_outputs_parked_before_regeneration=len(expected),all_non_time_outputs_equal=True,recorded_original_cost_fields_equal=True,real_primary_stops=True,python_S_extracted_origins=True,new_fitness_games=0,new_training=0,Core_commits=189063,Core_PV_edges=371850,independent_first_divergence_groups=382,isolated_native_build=True,new_fix_controls=10,steps=steps,verified_stage_seconds=sum(s['seconds']for s in steps),seconds=time.perf_counter()-started,scope='No sealed fitnessproducer/AUXTRAIN/oldfitnessrerun. Eleven derived outputs PARKED first; original recorded costs remain exact, only new execution seconds excluded. Source C built after all Core/math controls with Native ABSENT, then10actual fix controls. Declaredexistingexternaldependencies only, no editable-project fallthrough/fake flags/AUXcheckout.')
(O/'qualification.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());write_json(D/'fresh-qualification.json',q);print('FRESH_COMPLETE',q['verified_stage_seconds'],flush=True)
