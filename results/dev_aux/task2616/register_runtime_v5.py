"""Final pre-run pin amendment for task2616 after runner/audit/test completion."""
from pathlib import Path
import datetime,hashlib,json,shutil
D=Path(__file__).resolve().parent; ROOT=Path.cwd()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 pp,ep,rp=D/'plan.json',D/'eval-plan.json',D/'registration.json';reg=json.loads(rp.read_text(encoding='utf-8'))
 if reg.get('status')!='REGISTERED_PRE_RUN' or any((D/n).exists() for n in ('tree-started.json','eval-started.json','tree-training-result.json','eval-result.json')):raise RuntimeError('task is already started or not registered')
 a=D/'attempt-8';a.mkdir(exist_ok=False)
 for name,path in (('plan.json',pp),('eval-plan.json',ep),('registration.json',rp),('runner-registration.json',D/'runner-registration.json')):shutil.copy2(path,a/('before-final-audit-pin-'+name))
 plan=json.loads(pp.read_text(encoding='utf-8')); oldplan=reg['plan_sha256']; oldeval=reg['eval_plan_sha256']
 names=['results/dev_aux/task2616/train_tree.py','results/dev_aux/task2616/assemble.py','results/dev_aux/task2616/evaluate.py','results/dev_aux/task2616/summarize.py','results/dev_aux/task2616/audit.py','results/dev_aux/task2616/test_runner.py','results/dev_aux/task2616/register_runtime_v5.py','results/dev_aux/task2492/learning.py','results/dev_aux/task2492/adapters.py','results/dev_aux/task2504/search.py','results/dev_aux/task2565/train.py','results/dev_aux/task2392/reader.py','results/dev_aux/task2153/stop_evidence.py','results/dev_aux/task109/adapter.py','results/dev_aux/task2568/result.json','results/dev_aux/task2568/plan.json']
 pins={n:sha(ROOT/n) for n in names}; tr=plan['conditions']['training']; src=json.loads((ROOT/'results/dev_aux/task2568/plan.json').read_text(encoding='utf-8'))
 tr['training_family_offset']=src['training_family_offset'];tr['global_hard_cap_seconds']=1200;tr['ordering_seed_offset']=src['ordering_seed_offset']
 plan['sources']['task2568_training_plan_sha256']=sha(ROOT/'results/dev_aux/task2568/plan.json');plan['runtime_pins']=pins
 plan['amendment']={'version':5,'supersedes_plan_sha256':oldplan,'supersedes_eval_plan_sha256':oldeval,'reason':'Refresh final runtime source pins after replay-root assertions and budget regression tests. Training/evaluation arms, exact roots, endpoints and frozen caps remain unchanged; no run started.','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 pp.write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 rr={'task':'DEV_AUX2616','status':'READY_PRE_RUN','runtime_pins':pins,'plan_sha256':sha(pp),'eval_plan_sha256':sha(ep),'prior_plan_sha256':oldplan,'prior_eval_plan_sha256':oldeval,'no_training_yet':True,'no_evaluation_yet':True}
 (D/'runner-registration.json').write_text(json.dumps(rr,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 reg.update({'amendment':plan['amendment'],'plan_sha256':sha(pp),'eval_plan_sha256':sha(ep),'runner_registration_sha256':sha(D/'runner-registration.json'),'status':'REGISTERED_PRE_RUN','no_training_yet':True,'no_evaluation_yet':True})
 rp.write_text(json.dumps(reg,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 summary={'status':'AMENDED_PRE_RUN','version':5,'old_plan_sha256':oldplan,'new_plan_sha256':sha(pp),'old_eval_plan_sha256':oldeval,'new_eval_plan_sha256':sha(ep),'runtime_pins':pins,'conditions_changed':False}
 (a/'amendment.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8');return summary
if __name__=='__main__':print(json.dumps(main(),indent=2))
