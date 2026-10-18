"""Rebuild saved evidence from sealed baseline/product source, without Native or games."""
from pathlib import Path
import json,hashlib,zipfile,sys,subprocess,os,time,shutil,uuid
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;X=R/'.local_agent'/('acquisition-qualified-'+uuid.uuid4().hex[:10]);X.mkdir();began=time.perf_counter();steps=[]
def extract(p,target,prefix=None):
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None;m=json.loads(z.read('manifest.json'))
  for n,e in m['files'].items():
   b=z.read(n);assert len(b)==e['bytes']and hashlib.sha256(b).hexdigest()==e['sha256']
   if prefix is not None and not n.startswith(prefix):continue
   t=(target/n).resolve();assert t.is_relative_to(target.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b)
 return m
m=extract(O/'evidence.zip',X);dep=m['dependency'];p=O/dep['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==dep['sha256'];dm=extract(p,X/'source','source/');S=X/'source/source'
shutil.copytree(X/'data',S/'.local_agent',dirs_exist_ok=True)
env=dict(os.environ);env['PYTHONPATH']='';env['GC_REPLAY_STOP_ROOT']=str(R);site=Path(sys.prefix)/'Lib/site-packages'
def poll():
 for n in ['rollout','advisor','slack']:
  q=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(q.get('stopped')or q.get('user_paused')),'EXPLICIT_STOP'
def run(dn,name,cap=600):
 poll();tick=time.perf_counter();script=S/'.local_agent'/dn/name
 code='import sys,runpy,pathlib,importlib.util;sys.path[:0]='+repr([str(S),str(site)])+';assert importlib.util.find_spec("generic_chess._native_core") is None;runpy.run_path('+repr(str(script))+',run_name="__main__");assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path('+repr(str(S))+'))for k,v in sys.modules.items()if k.startswith("generic_chess")and getattr(v,"__file__",None))'
 with(X/(dn+'-'+name+'.log')).open('w',encoding='utf8')as f:
  p=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
  while p.poll()is None:
   try:poll();assert time.perf_counter()-tick<cap,'READER_CAP'
   except BaseException:p.terminate();p.wait();raise
   time.sleep(.25)
  assert p.returncode==0,(dn,name,p.returncode,str(X))
 steps.append(dict(directory=dn,script=name,seconds=time.perf_counter()-tick));print('QUALIFIED',steps[-1],flush=True)
def strip(v):
 if isinstance(v,dict):return{k:strip(x)for k,x in v.items()if k!='seconds'and not k.endswith('_seconds')}
 if isinstance(v,list):return[strip(x)for x in v]
 return v
expected={}
def park(dn,names):
 for name in names.split():
  p=S/'.local_agent'/dn/name;expected[dn,name]=json.loads(p.read_bytes());p.rename(p.with_name(name+'.sealed-original'))
a='acquisition-cost-20261018';b='acquisition-depth-cost-20261018';c='core-pipeline-cost-20261018';d='core-submit-product-binding-20261018';e='largeboard-submit-20261018'
park(a,'reader-result.json saved-root-import-cost.json analysis.json');park(b,'reader-result.json analysis.json rate-envelope.json');park(c,'analysis.json');park(d,'differential-result.json differential-started.json');park(e,'reader-result.json')
for dn,names in [(a,['reader.py','analyze.py']),(b,['reader.py','analyze.py','rate_envelope.py']),(c,['analyze.py'])]:
 for name in names:run(dn,name)
# Explicit product source overlay, only after baseline-source observations qualify.
product=X/'product/generic_chess/core/transition.py';assert hashlib.sha256(product.read_bytes()).hexdigest()==json.loads((S/'.local_agent'/d/'plan.json').read_bytes())['actual_product_transition_sha256'];shutil.copyfile(product,S/'generic_chess/core/transition.py')
script=S/'.local_agent'/d/'differential.py';original=script.read_bytes();text=original.decode('utf8');needle="(R/'.local_agent'/(n+'.json'))";assert text.count(needle)==1;text=text.replace(needle,"(Path(os.environ['GC_REPLAY_STOP_ROOT'])/'.local_agent'/(n+'.json'))");script.write_bytes(text.encode());expected[d,'differential-started.json']['source_sha256']=hashlib.sha256(script.read_bytes()).hexdigest()
run(d,'differential.py');run(e,'reader.py')
for (dn,name),v in expected.items():assert strip(v)==strip(json.loads((S/'.local_agent'/dn/name).read_bytes())),(dn,name)
q=dict(status='PASS_SEALED_BASELINE_AND_PRODUCT_SOURCE',own_payloads=len(m['files']),dependency_sha256=dep['sha256'],ten_outputs_parked_before_regeneration=True,all_non_time_fields_equal_except_explicit_stop_overlay_hash=True,native_absent=True,python_S_extracted_origins=True,real_primary_stops=True,product_overlay='Exact sealed product transition after baseline reader stages; actual public function differential, no private-candidate substitution.',stop_overlay='One read ROOT replacement in product differential only; original sealed source retained; corresponding started-source hash differs explicitly. No fake flags.',new_queries=0,new_generation=0,new_games=0,new_training=0,steps=steps,seconds=time.perf_counter()-began,scope='Full original roots/PV/gradient readers, recorded timing arithmetic, actual product34230children/3072invalid IDs, largerboard2209childhashes. Not timing replication, Native binary attestation, external rules authority, WDL or all-domain proof.')
tmp=O/'qualification.tmp';tmp.write_bytes((json.dumps(q,indent=2)+'\n').encode());os.replace(tmp,O/'qualification.json');print('SOURCE_PASS',q['seconds'],flush=True)
