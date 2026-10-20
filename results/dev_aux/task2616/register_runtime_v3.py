"""Final pre-run pin amendment for task2616 after executable runner review."""
from pathlib import Path
import datetime, hashlib, json, shutil
D=Path(__file__).resolve().parent
ROOT=Path.cwd()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    plan_path,eval_path,reg_path=D/'plan.json',D/'eval-plan.json',D/'registration.json'
    reg=json.loads(reg_path.read_text(encoding='utf-8'))
    if reg.get('status')!='REGISTERED_PRE_RUN' or any((D/name).exists() for name in ('tree-started.json','eval-started.json','tree-training-result.json','eval-result.json')):
        raise RuntimeError('cannot amend after training/evaluation has started')
    attempt=D/'attempt-6';attempt.mkdir(exist_ok=False)
    for name,path in (('plan.json',plan_path),('eval-plan.json',eval_path),('registration.json',reg_path),('runner-registration.json',D/'runner-registration.json')):
        shutil.copy2(path,attempt/('pre-final-pin-'+name))
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    task2568=json.loads((ROOT/'results/dev_aux/task2568/plan.json').read_text(encoding='utf-8'))
    tr=plan['conditions']['training']
    tr.update({
      'training_family_offset':task2568['training_family_offset'],
      'global_hard_cap_seconds':1200,
      'ordering_seed_offset':task2568['ordering_seed_offset'],
    })
    plan['sources']['task2568_training_plan_sha256']=sha(ROOT/'results/dev_aux/task2568/plan.json')
    names=[
      'results/dev_aux/task2616/train_tree.py','results/dev_aux/task2616/assemble.py',
      'results/dev_aux/task2616/evaluate.py','results/dev_aux/task2616/summarize.py',
      'results/dev_aux/task2616/test_runner.py','results/dev_aux/task2616/register_runtime_v3.py',
      'results/dev_aux/task2492/learning.py','results/dev_aux/task2492/adapters.py',
      'results/dev_aux/task2504/search.py','results/dev_aux/task2565/train.py',
      'results/dev_aux/task2392/reader.py','results/dev_aux/task2153/stop_evidence.py',
      'results/dev_aux/task109/adapter.py','results/dev_aux/task2568/result.json',
      'results/dev_aux/task2568/plan.json',
    ]
    pins={name:sha(ROOT/name) for name in names}
    old_plan=reg['plan_sha256'];old_eval=reg['eval_plan_sha256']
    plan['runtime_pins']=pins
    plan['sources']['eval_plan_sha256']=sha(eval_path)
    plan['amendment']={
      'version':3,'supersedes_plan_sha256':old_plan,'supersedes_eval_plan_sha256':old_eval,
      'reason':'Bind finalized trainer/evaluator/summary/tests and source-derived family/ordering/global limits before any run. Arms, roots, node/time caps and endpoints unchanged; no run started.',
      'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    plan_path.write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    # runner-registration itself is written after the new plan digest and stores that digest.
    runreg={
      'task':'DEV_AUX2616','status':'READY_PRE_RUN','runtime_pins':pins,
      'plan_sha256':sha(plan_path),'eval_plan_sha256':sha(eval_path),
      'prior_plan_sha256':old_plan,'prior_eval_plan_sha256':old_eval,
      'no_training_yet':True,'no_evaluation_yet':True,
    }
    (D/'runner-registration.json').write_text(json.dumps(runreg,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    reg.update({
      'amendment':plan['amendment'],'plan_sha256':sha(plan_path),'eval_plan_sha256':sha(eval_path),
      'status':'REGISTERED_PRE_RUN','no_training_yet':True,'no_evaluation_yet':True,
      'runner_registration_sha256':sha(D/'runner-registration.json'),
    })
    reg_path.write_text(json.dumps(reg,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    manifest={'status':'AMENDED_PRE_RUN','version':3,'old_plan_sha256':old_plan,'new_plan_sha256':sha(plan_path),
      'old_eval_plan_sha256':old_eval,'new_eval_plan_sha256':sha(eval_path),'runtime_pins':pins,
      'conditions_changed':False}
    (attempt/'amendment.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest
if __name__=='__main__':print(json.dumps(main(),indent=2))
