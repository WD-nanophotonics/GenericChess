from pathlib import Path
import json,subprocess,sys
R=Path.cwd();s=(R/'results/dev_aux/task1639/freeze_physical_train.py').read_text(encoding='utf-8-sig').replace("task1651'","task1658'").replace('2026680600','2026681600')
s=s.replace("json.loads((R/'results/dev_aux/task1640/plan.json').read_bytes())]","json.loads((R/'results/dev_aux/task1640/plan.json').read_bytes()),json.loads((R/'results/dev_aux/task1651/plan.json').read_bytes())]")
s=s.replace("a,b,c=pairs[f%3]","a,b,c=pairs[(f//2)%3];\n if f%2:a,b,c=a+4,b+4,c-4")
s=s.replace("'stock':['RNvsB','RBvsN','NBvsR'][f%3]","'stock':('OWN2_' if f%2==0 else 'OWN1_')+['RNvsB','RBvsN','NBvsR'][(f//2)%3]")
p=R/'results/dev_aux/task1639/freeze_balanced.py';p.write_text(s,encoding='utf8');subprocess.run([sys.executable,'-X','utf8',str(p)],check=True)
path=R/'results/dev_aux/task1658/plan.json';plan=json.loads(path.read_bytes());template=json.loads((R/'results/dev_aux/task1651/plan.json').read_bytes())
for key in ['objective','labels','primary_selector','handoff_horizon_plies','single_seconds','max_physical_go','expected_seconds','secondary_H48','no_mate_proof','opponent']:plan[key]=template[key]
plan['status']='FROZEN_BALANCED_OWN1_OWN2_NEW_ROOTS_BEFORE_QUERIES';plan['rootlaw']='Activecandidate alternatesone or twononkings,32each per64TRAIN and64each inDEV128. BothKingswithinCheby2, activeKingchecked>=2evasions, no immediatewinningmate. Uniformwhite D4representative+colorpair. RULE/PRICEblind sampling, excludesall priororbits. SamephysicalH48 objective/cold64/12grid/random; changedrootlaw notsamecohort replication.';plan['root_exclusions']=['task1630','task1633','task1640','task1651'];path.write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1639/physical_train.py').read_text(encoding='utf-8-sig').replace("task1652'","task1659'").replace('task1651/plan.json','task1658/plan.json')
s=s.replace("sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))","sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1652').glob('*choices.jsonl'))")
(R/'results/dev_aux/task1639/balanced_train.py').write_text(s,encoding='utf8')
print('BALANCED_OWN_ROLES_FROZEN',len(plan['families']))

