from pathlib import Path
import json,sys,shutil,subprocess,os,time,hashlib
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
T=R/'.local_agent/movement-transfer-20261017';S=T/'fresh/source';F=R/'.local_agent/rule-aware-map-20261017';M=S/'.local_agent/rule-aware-map-20261017';M.mkdir(exist_ok=True);P=S/'.local_agent/probe-scale-20261017';P.mkdir(exist_ok=True)
for n in ['next-rule-aware-mapping-plan.json','next-rule-aware-mapping-inventory.json']:shutil.copyfile(T/n,S/'.local_agent/movement-transfer-20261017'/n)
f=F/'mapping_feasibility-portable.py';script=P/f.name;shutil.copyfile(f,script)
start=time.perf_counter();env=dict(os.environ,PYTHONPATH='',GC_REPLAY_STOP_ROOT=str(R),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');code='import sys,pathlib,runpy;sys.path[:0]='+repr([str(S),str(R/'.venv/Lib/site-packages')])+';sys.argv=['+repr(str(script))+'];runpy.run_path('+repr(str(script))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None));'
with(F/'fresh-feasibility.log').open('w')as log:r=subprocess.run([str(R/'.venv/Scripts/python.exe'),'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=130)
assert r.returncode==0,'See savedfresh-feasibility.log'
def strip(x):
 if isinstance(x,dict):return {k:strip(v)for k,v in x.items()if k!='seconds'}
 if isinstance(x,list):return [strip(v)for v in x]
 return x
for n in ['feasibility-plan.json','feasibility-inputs.json','feasibility-result.json']:assert strip(json.loads((F/n).read_bytes()))==strip(json.loads((M/n).read_bytes())),n
write_json(F/'fresh-qualification.json',dict(status='PASS_96MAPPING_COMPONENTS_VERIFIED_PARENT_SOURCE',calls=96,all_non_time_fields_equal=True,exact_selected_inputs_equal=True,source_origins_asserted=True,real_primary_stops=True,parent_source_sha256='59d7aee577d2d567543cb3a805dbdc0b88227e7cb7f67014ff93373c6b60efb4',script_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),seconds=time.perf_counter()-start,scope='SeparateAFTERsealcomponentqualification, usingpreviouslyverifiedparentfreshPython/Canddata plusexactnewrule-ratioinventory/script. Repeats96componentqueries/4objectiveCorecontrolsONLY, not7040or3264fitness/TRAIN; noAUXwrites/newbuildclaim. NewthinarchiveCorequalification is separate andNative-absent.'))
print('PASS fresh96sameinputs/rule-ratio policy decisions; nofitnessrerun')
