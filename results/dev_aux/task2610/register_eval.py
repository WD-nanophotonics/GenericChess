"""Pre-register a second outcome-blind root panel for frozen task2606 models."""
from pathlib import Path
from collections import defaultdict
import datetime, hashlib, json

D=Path('results/dev_aux/task2610')
assert D.exists() and not any((D/n).exists() for n in ('root-manifest.json','eval-plan.json','registration.json','eval-binding.json','eval-started.json','eval-result.json','eval-games.jsonl','eval-queries.jsonl'))
load=lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
old_candidates=Path('results/dev_aux/task2607/root-candidates.json')
old_result=load('results/dev_aux/task2607/result.json')
old_reg=load('results/dev_aux/task2607/registration.json')
old_plan=load('results/dev_aux/task2607/plan.json')
assert old_result['status']=='PASS'
assert old_reg['state']=='REGISTERED_BEFORE_AUDIT'
assert sha('results/dev_aux/task2607/plan.json')==old_reg['plan_sha256']
assert sha(old_candidates)==old_result['root_rows_sha256']
for path,digest in old_reg['source_pins'].items(): assert sha(path)==digest,path
candidates=load(old_candidates)
old_manifest=load('results/dev_aux/task2609/root-manifest.json')
old_plan_eval=load('results/dev_aux/task2609/eval-plan.json')
old_reg_eval=load('results/dev_aux/task2609/registration.json')
old_eval=load('results/dev_aux/task2609/eval-result.json')
train=load('results/dev_aux/task2606/result.json')
assert train['status']=='COMPLETE' and old_eval['status']=='COMPLETE' and old_eval['actual']==1536
assert sha('results/dev_aux/task2609/eval-plan.json')==old_reg_eval['eval_plan_sha256']
assert sha('results/dev_aux/task2609/root-manifest.json')==old_reg_eval['root_manifest_sha256']
prior={(int(key.split(':')[0]),int(key.split(':')[1])):rec for key,rec in old_manifest['roots'].items()}
# The source candidate order and VALID_AFTER_TARGET classes were materialized before task2609 saw fitness.
selected={}; roots={}; counts={}
for rule in old_plan['rules']:
    rows=sorted((r for r in candidates if r['rule']==rule and r['reason']=='VALID_AFTER_TARGET'),key=lambda r:r['family'])
    assert len(rows)>=16
    take=rows[:16]
    records=[json.dumps(r['record'],sort_keys=True,separators=(',',':'),ensure_ascii=False) for r in take]
    assert len(set(records))==16
    for row,rec in zip(take,records):
        family=row['family']; key=(rule,family)
        assert key not in prior
        assert len(row['record']['actions'])==old_plan['prefix_plies']==4
        assert not any(json.dumps(old,sort_keys=True,separators=(',',':'),ensure_ascii=False)==rec for (rr,_),old in prior.items() if rr==rule)
        roots[f'{rule}:{family}']=row['record']
    selected[str(rule)]=[r['family'] for r in take]
    counts[str(rule)]={'eligible_precomputed':len(rows),'selected':len(take),'first_family':take[0]['family'],'last_family':take[-1]['family']}
slots=[[rule,seed,family,color,endpoint,'uniform'] for rule in old_plan['rules'] for seed in old_plan_eval['seeds'] for family in selected[str(rule)] for color in (0,1) for endpoint in ('initial','TD95','LocalLambda')]
assert len(slots)==1536
(D/'root-manifest.json').write_text(json.dumps({'state':'FROZEN_BEFORE_EVALUATION','identity':old_plan['identity'],'prefix_plies':4,'source_candidates_sha256':sha(old_candidates),'prior_panel_manifest_sha256':sha('results/dev_aux/task2609/root-manifest.json'),'selection_rule':'Per rule, ascending family ID, first 16 rows preclassified VALID_AFTER_TARGET in the task2607 outcome-blind candidate artifact. Those rows are legal nonterminal 4-ply records absent all 512 potential training start records and unique from the original task2609 panel. Selection reads no outcomes.','selected_families':selected,'roots':roots},indent=2,sort_keys=True)+'\n',encoding='utf-8')
train_path=Path('results/dev_aux/task2606/result.json')
plan={'state':'REGISTERED_BEFORE_EVALUATION','task':'DEV_AUX2610','purpose':'Evaluation-only second root panel for the frozen task2606 learner models; no retraining or parameter selection.','question':'Does LocalLambda-minus-TD95 on the fixed task2606 models reproduce the task2609 finite-panel contrast on a second pre-outcome-classified, exact-start-history-disjoint root panel?','changed_premise':'task2609 already crossed its same 16 roots per rule across all four parameter seeds; repeating that root block would be redundant. This panel uses the next first-16 VALID_AFTER_TARGET records from task2607s candidate stream.','model_source':'Frozen task2606/result.json; all 32 trained arms and initial weights fixed.','models_sha256':sha(train_path),'rules':old_plan['rules'],'seeds':old_plan_eval['seeds'],'endpoints':['initial','TD95','LocalLambda'],'foes':{'uniform':[1.0]*6},'depth':2,'H':128,'nodes_per_query':8192,'seconds_per_query':2,'cap_seconds':1200,'expected_duration_minutes':12,'prefix_plies':4,'slots':slots,'root_manifest_sha256':sha(D/'root-manifest.json'),'selection':'For each rule take the 16 lowest family IDs already classified VALID_AFTER_TARGET in task2607/root-candidates.json. task2607 classification and source candidate pool predate task2609 evaluation. They are distinct from the prior task2609 roots and every 512 possible task2606 training-family start root by that frozen classification. No outcome inspection or post-result root selection. The target is this finite accepted-root panel; not the unconditional family distribution or a descendant-state holdout.','interpretation':'Same frozen models, four fixed parameter seeds, three endpoints, same uniform foe, color balancing and search budget as task2609; identical new roots are crossed across all seeds/endpoints. UNKNOWN remains censored and paired UNKNOWN bounds remain [-2,+2]. The second panel assesses sensitivity to root block for these models, not new-seed variability or population generalization. Preserve both panels; do not select between them.','source_pins':{}}
pins=['results/dev_aux/task2606/train.py','results/dev_aux/task2606/result.json','results/dev_aux/task2607/plan.json','results/dev_aux/task2607/registration.json','results/dev_aux/task2607/result.json','results/dev_aux/task2607/root-candidates.json','results/dev_aux/task2609/root-manifest.json','results/dev_aux/task2609/eval-plan.json','results/dev_aux/task2609/eval-result.json','results/dev_aux/task2609/run_eval.py','results/dev_aux/task2610/register_eval.py','results/dev_aux/task2610/run_eval.py']+[f'results/dev_aux/task2525/rules-{r}.json' for r in old_plan['rules']]
plan['source_pins']={p:sha(p) for p in pins}
(D/'eval-plan.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
reg={'state':'REGISTERED_BEFORE_EVALUATION','registered_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'DEV_AUX2610','models_sha256':plan['models_sha256'],'root_manifest_sha256':plan['root_manifest_sha256'],'eval_plan_sha256':sha(D/'eval-plan.json'),'source_pins':plan['source_pins'],'expected_slots':1536,'hard_cap_seconds':1200,'fitness_started':False}
(D/'registration.json').write_text(json.dumps(reg,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'registered':True,'task':reg['task'],'slots':1536,'root_counts':counts,'root_manifest_sha256':plan['root_manifest_sha256'],'eval_plan_sha256':reg['eval_plan_sha256'],'registration_sha256':sha(D/'registration.json'),'expected_minutes':12,'cap_seconds':1200},indent=2))
