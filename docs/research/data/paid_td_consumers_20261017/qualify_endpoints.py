from pathlib import Path
import json,sys,shutil,subprocess,os,time
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
T=R/'.local_agent/movement-transfer-20261017';q=json.loads((T/'fresh-qualification.json').read_bytes());assert q['status'].startswith('PASS')
D=R/'.local_agent/paid-td-20261017';S=T/'fresh/source';M=S/'.local_agent/paid-td-20261017';M.mkdir(parents=True);A=M/'exact/results/dev_aux/task2525';A.mkdir(parents=True)
for n in ['endpoint_consumer.py','endpoint-plan.json','endpoint-inputs.json']:shutil.copyfile(D/n,M/n)
for gs in [271001,271002,271003,271004]:shutil.copyfile(D/'exact/results/dev_aux/task2525'/f'rules-{gs}.json',A/f'rules-{gs}.json')
site=R/'.venv/Lib/site-packages';code='import sys,runpy,pathlib;sys.path[:0]='+repr([str(S),str(site)])+';sys.argv=['+repr(str(M/'endpoint_consumer.py'))+'];runpy.run_path('+repr(str(M/'endpoint_consumer.py'))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None));'
env=dict(os.environ,PYTHONPATH='',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',GC_REPLAY_STOP_ROOT=str(R));start=time.perf_counter()
with(D/'fresh-endpoints.log').open('w')as log:r=subprocess.run([str(R/'.venv/Scripts/python.exe'),'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=130)
assert r.returncode==0,'See savedfresh-endpoints.log'
def strip(x):
 if isinstance(x,dict):return {k:strip(v)for k,v in x.items()if k not in ('seconds','caller_seconds')}
 if isinstance(x,list):return [strip(v)for v in x]
 return x
assert strip(json.loads((D/'endpoint-result.json').read_bytes()))==strip(json.loads((M/'endpoint-result.json').read_bytes()))
write_json(D/'fresh-endpoint-qualification.json',dict(status='PASS_128ACTUAL92_NATIVE_COMPONENTS_EXTRACTED_SOURCE',fresh_source_capsule_sha=q['zip_sha256'],source_origin_asserted=True,actual_92_inputs=128,new_negativeP_model_inputs=16,all_non_time_fields_equal=True,source_gradient_missing_preserved=True,existing_fresh_source_and_C_reused=True,real_primary_stops=True,seconds=time.perf_counter()-start,scope='SeparateAFTERseal92supplement, NOTanoriginal186-payloadmember/qualificationoutput. Minimalfixed92rules+fullselectedinputs/read-onlycheckpointconsumer hydrated into verifiedfreshPRIMARYsource; actual128queries rerunonlyascomponentqualification, nooriginal1536EVAL/TRAINrerun/AUXimports/defaultactivation. ExcludesONLYnewexecution/percallclocks.'))
print('PASS separateactual92component fresh128, no originalfitnessrerun')
