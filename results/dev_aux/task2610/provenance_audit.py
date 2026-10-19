from pathlib import Path
import hashlib,json
R=Path('results/dev_aux/task2610'); A=R/'attempt-2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parent=json.loads((R/'registration.json').read_text())
reg=json.loads((A/'registration.json').read_text())
plan=json.loads((A/'eval-plan.json').read_text())
binding=json.loads((A/'eval-binding.json').read_text())
result=json.loads((A/'eval-result.json').read_text())
failure=R/'attempt-1-failure.json'
assert sha(R/'eval-plan.json')==parent['eval_plan_sha256']
assert sha(R/'root-manifest.json')==parent['root_manifest_sha256']
assert sha(R/'registration.json')==reg['parent_registration_sha256']
assert sha(A/'eval-plan.json')==sha(R/'eval-plan.json')==reg['eval_plan_sha256']
assert sha(A/'root-manifest.json')==sha(R/'root-manifest.json')==reg['root_manifest_sha256']
assert sha(failure)==reg['attempt1_failure_sha256']
assert reg['model_result_sha256']==reg['models_sha256']==plan['models_sha256']==binding['models_sha256']
assert binding['plan_sha256']==reg['eval_plan_sha256']
assert binding['root_manifest_sha256']==reg['root_manifest_sha256']
pins={}
for path,digest in reg['source_pins'].items():
    actual=sha(path)
    assert actual==digest,path
    pins[path]=actual
assert result['status']=='COMPLETE' and result['expected']==result['actual']==1536 and result['missing']==0
assert result['seconds']<plan['cap_seconds'] and plan['cap_seconds']==1200
assert not (A/'attempt-1-failure.json').exists()
assert not any((A/x).exists() for x in ('train-started.json','training-result.json'))
out={'status':'PASS','parent_registration_sha256':sha(R/'registration.json'),
 'attempt2_registration_parent_sha256':reg['parent_registration_sha256'],
 'plan_sha256':reg['eval_plan_sha256'],'root_manifest_sha256':reg['root_manifest_sha256'],
 'attempt1_failure_sha256':sha(failure),'model_result_sha256':reg['model_result_sha256'],
 'source_pins_checked':len(pins),'slots':result['actual'],'seconds':result['seconds'],
 'training_started':False,'registration_correction':'alias-only; models/plan/roots/cap unchanged'}
(R/'provenance-audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2))
