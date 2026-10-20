from pathlib import Path
from collections import defaultdict
import hashlib, json
D=Path(__file__).parent
BASE=D.parent
ROOT=D.parents[2]
R=json.loads((D/'result.json').read_text(encoding='utf-8'))
checks=[]
def check(panel,contrast,expected):
    got=next(x for x in R['panels'][panel]['contrasts'] if x['contrast']==contrast)['old_blanket_mean_bound']
    assert got==expected,(panel,contrast,got,expected)
    checks.append({'panel':panel,'contrast':contrast,'old_bound_reproduced':got})
# Reproduce every interval that appeared in the earlier machine-readable reports.
a=json.loads((BASE/'task2606/analysis.json').read_text(encoding='utf-8'))['LocalLambda_pairwise_bounds']
check('task2606','LocalLambda-initial',[a['initial']['finite_panel_mean_lower'],a['initial']['finite_panel_mean_upper']])
check('task2606','LocalLambda-TD95',[a['TD95']['finite_panel_mean_lower'],a['TD95']['finite_panel_mean_upper']])
a=json.loads((BASE/'task2609/audit.json').read_text(encoding='utf-8'))['paired_reward_bounds']
for row in a: check('task2609',f"{row['left']}-{row['right']}",row['difference_mean_bounds'])
a=json.loads((BASE/'task2610/panel-comparison.json').read_text(encoding='utf-8'))['panels']
for row in a:
    if row['panel']=='task2610': check('task2610',row['contrast'],row['mean_bound'])
# Verify the frozen manifests themselves are the exact plans bound by the original registrations.
plan_bindings=[]
for plan_path,binding_path,field in [
    (BASE/'task2606/eval-plan.json',BASE/'task2606/eval-binding.json','plan_sha'),
    (BASE/'task2609/eval-plan.json',BASE/'task2609/registration.json','eval_plan_sha256'),
    (BASE/'task2610/attempt-2/eval-plan.json',BASE/'task2610/attempt-2/registration.json','eval_plan_sha256')]:
    expected=json.loads(binding_path.read_text(encoding='utf-8'))[field]
    actual=hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert actual==expected,(str(plan_path),actual,expected)
    plan_bindings.append({'plan':str(plan_path.relative_to(ROOT)).replace('\\','/'),'sha256':actual,'registration_field':field})
started=json.loads((D/'started.json').read_text(encoding='utf-8'))
for name,expected in started['source_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,(name,'started pin mismatch')
    if name in R['input_sha256']: assert R['input_sha256'][name]==expected,(name,'result input pin mismatch')
    if name in R['source_sha256']: assert R['source_sha256'][name]==expected,(name,'result source pin mismatch')
# Confirm each saved row is exactly in its frozen manifest and each pair used the same foe.
slot_checks=[]
files={
 'task2606':(BASE/'task2606/eval-plan.json',BASE/'task2606/eval-games.jsonl'),
 'task2609':(BASE/'task2609/eval-plan.json',BASE/'task2609/eval-games.jsonl'),
 'task2610':(BASE/'task2610/attempt-2/eval-plan.json',BASE/'task2610/attempt-2/eval-games.jsonl')}
for name,(plan_path,games_path) in files.items():
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in games_path.read_text(encoding='utf-8-sig').splitlines() if x]
    frozen={tuple(x) for x in plan['slots']}
    seen={tuple(x['slot']) for x in rows}
    assert len(rows)==len(frozen) and seen==frozen,(name,len(rows),len(frozen),len(seen))
    grouped=defaultdict(set)
    for row in rows:
        rule,seed,family,color,endpoint,foe=row['slot']
        assert endpoint in ('initial','TD95','LocalLambda')
        assert row['reward'] is None or row['reward'] in (-1,0,1)
        grouped[(rule,seed,family,color,endpoint)].add(foe)
    for (rule,seed,family,color,endpoint),foes in grouped.items():
        assert len(foes)==1,(name,rule,seed,family,color,endpoint,foes)
    pairs=defaultdict(dict)
    for row in rows:
        rule,seed,family,color,endpoint,foe=row['slot']
        pairs[(rule,seed,family,color)][endpoint]=foe
    assert all(set(v)=={'initial','TD95','LocalLambda'} and len(set(v.values()))==1 for v in pairs.values())
    slot_checks.append({'panel':name,'rows':len(rows),'frozen_slots':len(frozen),'exact_manifest_match':True,'paired_foe_match':True})
# Aggregate identity for each contrast: only unknown endpoints range over [-1,+1].
formula_checks=[]
for panel in ('task2606','task2609','task2610'):
    p=R['panels'][panel]
    for row in p['contrasts']:
        left,right=row['contrast'].split('-')
        wl=p['wdl_by_endpoint'][left]; wr=p['wdl_by_endpoint'][right]; n=row['strata']
        sl=wl.get('WIN',0)-wl.get('LOSS',0); sr=wr.get('WIN',0)-wr.get('LOSS',0)
        ul=wl.get('UNKNOWN',0); ur=wr.get('UNKNOWN',0)
        expected=[(sl-ul-sr-ur)/n,(sl+ul-sr+ur)/n]
        assert expected==row['tight_mean_bound'],(panel,row['contrast'],expected,row['tight_mean_bound'])
        assert n==p['rows']//3
        formula_checks.append({'panel':panel,'contrast':row['contrast'],'tight_bound':expected,'strata':n})
paths=[*files['task2606'],*files['task2609'],*files['task2610'],BASE/'task2606/analysis.json',BASE/'task2609/audit.json',BASE/'task2610/panel-comparison.json',D/'result.json',D/'reaggregate.py']
result={
 'task':'DEV_AUX2615','status':'PASS',
 'old_interval_reproduction_checks':checks,
 'frozen_slot_checks':slot_checks,
 'plan_registration_bindings':plan_bindings,
 'tight_bound_formula_checks':formula_checks,
 'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
 'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'interpretation':'Old blanket bounds exactly reproduce the published machine summaries. Frozen manifests and matched foes were verified. Tight bounds match sum-difference +/- unknown endpoint counts. These are exact finite-panel completion bounds, not confidence intervals or population effects.'}
(D/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
