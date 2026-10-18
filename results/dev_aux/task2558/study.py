"""One serial producer for registered candidate-D3 learning and fixed-policy deployment."""
from pathlib import Path
import json,subprocess,sys,hashlib,datetime
D=Path('results/dev_aux/task2558');E=Path('results/dev_aux/task2559')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 assert not(D/'orchestration-started.json').exists();p0=json.loads((E/'plan.json').read_text());registered=sha(E/'plan.json');(D/'orchestration-started.json').write_text(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),registered_eval_plan_sha=registered,source_sha=sha(Path(__file__)),prior_depth_matrix_closed=True)))
 subprocess.run([sys.executable,'-X','utf8','-m','results.dev_aux.task2558.run'],check=True)
 new=json.loads((D/'result.json').read_text());arms=list(new['arms'])
 # Both depth policies start from the same random coefficient recipe; never pick a seed/model on outcomes.
 initial={}
 for a in arms:
  key=a['generator_seed'],a['seed'];assert key not in initial or initial[key]==a['initial'];initial[key]=a['initial']
 models=dict(status='COMPLETE'if new['status']=='COMPLETE'else'PARTIAL_CAP',arms=arms,expected_arms=32,sources={'prospective':'results/dev_aux/task2558/result.json'},selection='ALLavailable prospective endpoints incl partial arm; absent arms remain missing EVAL slots');(E/'models.json').write_text(json.dumps(models,indent=2))
 assert sha(E/'plan.json')==registered;p=json.loads((E/'plan.json').read_text());more=[D/'result.json',D/'pins.json',E/'models.json',Path('results/dev_aux/task2504/search.py'),Path('results/dev_aux/task2532/free_model.py'),Path('results/dev_aux/task2525/run.py'),Path('results/dev_aux/task2392/reader.py')]+[Path(f'results/dev_aux/task2525/rules-{gs}.json')for gs in p['generator_seeds']]
 p['pins'].update({f.as_posix():sha(f)for f in more});(E/'plan.json').write_text(json.dumps(p,indent=2));(E/'pre-fitness-binding.json').write_text(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),registered_eval_plan_sha=registered,plan_sha=sha(E/'plan.json'),models_sha=sha(E/'models.json'),actual_source_arms=len(arms),all_models_retained=True,selection='Only result/hash binding added to prewritten plans; no model/slot/seed/rule/root selection',train_status=new['status']),indent=2))
 subprocess.run([sys.executable,'-X','utf8','-m','results.dev_aux.task2559.evaluate'],check=True)
 (D/'orchestration-ended.json').write_text(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='TRAIN_AND_NEW_D3_DEPLOYMENT_CLOSED')))
if __name__=='__main__':run()
