from pathlib import Path
import json,hashlib,random
from results.dev_aux.task2606.train import compiled,restore
R=Path('results/dev_aux')
candidates=json.loads((R/'task2607/root-candidates.json').read_text())
old=[]
for d in ('task2609','task2610/attempt-2'):
    m=json.loads((R/d/'root-manifest.json').read_text())
    old.append((R/d/'root-manifest.json',m))
used={family for _,m in old for roots in m['selected_families'].values() for family in roots}
old_identities=set()
for _,m in old:
    for key,record in m['roots'].items():
        rule=int(key.split(':',1)[0])
        old_identities.add((rule,record['ruleset_fingerprint'],json.dumps(record,sort_keys=True,separators=(',',':'))))
reg=json.loads((R/'task2610/attempt-2/registration.json').read_text())
candidate_sha=hashlib.sha256((R/'task2607/root-candidates.json').read_bytes()).hexdigest()
assert candidate_sha==reg['source_pins']['results/dev_aux/task2607/root-candidates.json']
selection={}; counts={}
for rule in (271001,271002,271003,271004):
    valid=sorted((x for x in candidates if x['rule']==rule and x['reason']=='VALID_AFTER_TARGET'),key=lambda x:x['family'])
    counts[str(rule)]={'valid_total':len(valid),'used_panel_families':[x['family'] for x in valid if x['family'] in used]}
    remaining=[]
    for x in valid:
        key=(rule,x['record']['ruleset_fingerprint'],json.dumps(x['record'],sort_keys=True,separators=(',',':')))
        if x['family'] not in used and key not in old_identities:
            remaining.append(x)
    selection[str(rule)]=remaining[:16]
    assert len(selection[str(rule)])==16
identities=set()
for rule,rows in selection.items():
    for row in rows:
        key=(int(rule),row['record']['ruleset_fingerprint'],json.dumps(row['record'],sort_keys=True,separators=(',',':')))
        assert key not in identities and key not in old_identities
        env=restore(int(rule),compiled(int(rule)),row['record'])
        assert env.record()==row['record'] and env.terminal() is None and len(row['record']['actions'])==4
        identities.add(key)
seeds=sorted(random.Random(2611).sample(range(1,1_000_000),4))
prior_seed_sets={task:sorted({a['seed'] for a in json.loads((R/task/'result.json').read_text()).get('arms',[]) if 'seed' in a}) for task in ('task2594','task2606')}
assert all(not set(seeds)&set(values) for values in prior_seed_sets.values())
training_result_path=R/'task2606/result.json'
training_seconds=float(json.loads(training_result_path.read_text())['seconds'])
training_plan_path=R/'task2606/plan.json'
training_cap=json.loads(training_plan_path.read_text())['cap_seconds']
evaluation_plan_path=R/'task2610/attempt-2/eval-plan.json'
evaluation_cap=json.loads(evaluation_plan_path.read_text())['cap_seconds']
evaluation_paths=[R/'task2609/eval-result.json',R/'task2610/attempt-2/eval-result.json']
evaluation_seconds=[float(json.loads(path.read_text())['seconds']) for path in evaluation_paths]
evaluation_estimate=max(evaluation_seconds)
assert training_seconds <= training_cap and all(seconds <= evaluation_cap for seconds in evaluation_seconds)
assert training_cap + evaluation_cap < 7200 and training_seconds + evaluation_estimate < 7200
cost_sources=[training_result_path,training_plan_path,evaluation_plan_path,*evaluation_paths]
result={
 'task':'DEV_AUX2611_FEASIBILITY_ONLY',
 'candidate_source_sha256':candidate_sha,
 'pre_outcome_source':'task2607 outcome-blind deterministic scan; classification predates task2609 and task2610',
 'old_root_manifests':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path,m in old},
 'valid_candidate_counts_and_used':counts,
 'proposed_third_panel':{r:[x['family'] for x in rows] for r,rows in selection.items()},
 'proposed_new_seeds':seeds,
 'prior_seed_sets_checked':prior_seed_sets,
 'training_arms':32,'nodes_per_arm':312500,'total_training_nodes':10000000,
 'observed_training_wall_seconds_task2606':training_seconds,
 'training_cap_seconds':training_cap,
 'evaluation_slots':1536,'expected_evaluation_seconds_task2609_2610':evaluation_seconds,
 'cost_source_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in cost_sources},
 'evaluation_cap_seconds':evaluation_cap,
 'configured_training_plus_evaluation_cap_seconds':training_cap+evaluation_cap,
 'configured_cap_minutes':(training_cap+evaluation_cap)/60,
 'remaining_cap_headroom_to_120min_seconds':7200-(training_cap+evaluation_cap),
 'estimated_combined_seconds':training_seconds+evaluation_estimate,
 'estimated_combined_minutes':(training_seconds+evaluation_estimate)/60,
 'purpose':'If pursued, train all four rules × four new deterministic seeds × both fixed learner arms from scratch at the same nodes-per-arm, then evaluate on the next 16 eligible roots/rule, same uniform foe, endpoint/color/depth/node/H conditions. Distinguishes learner-seed replication using a new root panel; no model or root selection from 2609/2610 outcomes.',
 'preflight_replayed_roots':len(identities),
 'status':'FEASIBLE DESIGN ONLY; NOT REGISTERED OR RUN',
 'limits':['One four-seed batch remains small and cannot establish population effects.','Evaluation-root selection is deterministic from the existing pre-outcome candidate stream, not a random sample.','Combined observed-stage estimate is ~69.5 minutes; the 110-minute sum of configured training/evaluation caps leaves only 10 minutes for setup/audit before the 120-minute assessment boundary. Include actual preparation and audit time in the estimate; actual must be reported.']
}
(R/'task2611/feasibility.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
existing_md=(R/'task2611/FEASIBILITY.md').read_text(encoding='utf-8')
header=existing_md.split('\n{\n',1)[0].rstrip()+'\n\n'
(R/'task2611/FEASIBILITY.md').write_text(header+json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
