"""Register a new evaluation-only panel for frozen task2606 models."""
from pathlib import Path
import datetime,hashlib,json
D=Path('results/dev_aux/task2608'); assert not any((D/n).exists() for n in ('eval-plan.json','root-manifest.json','registration.json','eval-started.json'))
R=json.loads(Path('results/dev_aux/task2607/result.json').read_text(encoding='utf-8')); assert R['status']=='PASS'
rows=json.loads(Path('results/dev_aux/task2607/root-candidates.json').read_text(encoding='utf-8'))
selected={}; roots={}
for gs in (271001,271002,271003,271004):
 ok=[r for r in rows if r['rule']==gs and r['reason']=='ACCEPT_FIRST_16']; assert len(ok)==16
 selected[gs]=[r['family'] for r in ok]
 roots.update({f'{gs}:{r["family"]}':r['record'] for r in ok})
root={'state':'FROZEN_BEFORE_EVALUATION','identity':'Exact complete GameSession record including ruleset fingerprint and all four actions.','task2607_result_sha256':hashlib.sha256(Path('results/dev_aux/task2607/result.json').read_bytes()).hexdigest(),'roots':roots,'selected_families':selected}
(D/'root-manifest.json').write_text(json.dumps(root,indent=2,sort_keys=True)+'\n',encoding='utf-8')
train=json.loads(Path('results/dev_aux/task2606/result.json').read_text(encoding='utf-8')); assert train['status']=='COMPLETE' and len(train['arms'])==32
slots=[[gs,seed,fam,color,endpoint,'uniform'] for gs in selected for seed in (1977,8173,27182,31415) for fam in selected[gs] for color in (0,1) for endpoint in ('initial','TD95','LocalLambda')]
assert len(slots)==1536
pins={}
for p in ('results/dev_aux/task2606/train.py','results/dev_aux/task2606/result.json','results/dev_aux/task2607/plan.json','results/dev_aux/task2607/registration.json','results/dev_aux/task2607/result.json','results/dev_aux/task2607/root-candidates.json','results/dev_aux/task2608/register_eval.py','results/dev_aux/task2608/run_eval.py'):
 pins[p]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
for gs in selected:
 p=f'results/dev_aux/task2525/rules-{gs}.json';pins[p]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
eval_plan={'state':'REGISTERED_BEFORE_EVALUATION','task':'DEV_AUX2608','purpose':'Evaluate fixed task2606 models on a new exact-record-disjoint rule/history root panel; no retraining or coefficient selection.','question':'Do the frozen task2606 TD95 and LocalLambda endpoints retain their finite-panel outcomes on exact start histories disjoint from all 512 task2606 training-family roots?','model_source':'Frozen task2606/result.json; all 32 learned models and their initial weights are fixed.','models_sha256':hashlib.sha256(Path('results/dev_aux/task2606/result.json').read_bytes()).hexdigest(),'rules':[271001,271002,271003,271004],'seeds':[1977,8173,27182,31415],'endpoints':['initial','TD95','LocalLambda'],'foes':{'uniform':[1.0]*6},'depth':2,'H':128,'nodes_per_query':8192,'seconds_per_query':2,'cap_seconds':1200,'expected_duration_minutes':10,'slots':slots,'root_manifest_sha256':hashlib.sha256((D/'root-manifest.json').read_bytes()).hexdigest(),'task2607_disjointness':'Selected by fixed ascending family-ID scan using the first16 unique valid records disjoint from the full 512-family potential training-root set per rule. Root identities bind ruleset_fingerprint and complete GameSession action history. No outcomes used in root selection. This guarantees start-root disjointness only, not disjoint descendant positions.'}
(D/'eval-plan.json').write_text(json.dumps(eval_plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
reg={'state':'REGISTERED_BEFORE_EVALUATION','registered_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'DEV_AUX2608','model_result_sha256':eval_plan['models_sha256'],'root_manifest_sha256':eval_plan['root_manifest_sha256'],'eval_plan_sha256':hashlib.sha256((D/'eval-plan.json').read_bytes()).hexdigest(),'source_pins':pins,'expected_slots':len(slots),'hard_cap_seconds':1200,'training_or_fitness_started':False}
(D/'registration.json').write_text(json.dumps(reg,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'registered':True,'slots':len(slots),'unique_roots':len(roots),'expected_minutes':10,'hard_cap_seconds':1200,'model_sha256':reg['model_result_sha256'],'eval_plan_sha256':reg['eval_plan_sha256'],'root_manifest_sha256':reg['root_manifest_sha256']}))