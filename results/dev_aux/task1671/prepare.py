from pathlib import Path
import ast,json,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1671'
s=(R/'results/dev_aux/task1639/freeze_balanced_fixed.py').read_text(encoding='utf-8-sig').split("s=(R/")[0]
s=s.replace('task1660','task1672').replace('[1630,1633,1640,1651]','[1630,1633,1640,1651,1660]').replace('2026681600','2026683600').replace("'task1651']","'task1651','task1660']")
s+='\nnew=plan; old=json.loads((R/"results/dev_aux/task1666/plan.json").read_bytes()); old.update({k:new[k] for k in ["families","seed","attempts","root_exclusions","rootlaw"]}); old.update(status="FROZEN_NATIVE_OPPONENT_NEW_ROOT_REPLICATION",source_base="8ac8a9fc44354cc84ff5fbfe5e3361cb844be050",expected_seconds=200); (O/"plan.json").write_text(json.dumps(old,indent=2));\n'
(O/'freeze.py').write_text(s,encoding='utf8')
s=(R/'results/dev_aux/task1639/native_opponent.py').read_text(encoding='utf-8-sig').replace('task1667','task1673').replace('task1666/plan.json','task1672/plan.json')
s=s.replace("sorted((R/'results/dev_aux/task1661').glob('*choices.jsonl')):","sorted((R/'results/dev_aux/task1661').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1667').glob('*choices.jsonl')):")
(O/'learn.py').write_text(s,encoding='utf8')
s=(R/'results/dev_aux/task1639/audit_native_opponent.py').read_text(encoding='utf-8-sig').replace('task1668','task1674').replace("task1666/plan.json","task1672/plan.json")
s=s.replace("'task1661','task1667']","'task1661','task1667','task1673']").replace("folder=='task1667'","folder=='task1673'").replace("P=R/'results/dev_aux/task1667'","P=R/'results/dev_aux/task1673'")
s=s.replace("'task1640','task1651']","'task1640','task1651','task1660']").replace("assert counts['games']==4096","assert counts['games']==3072+256*len(run['DEV'])")
s=s.replace('ROOTfamilies reusedbalanced1660: changedopponent/windowmechanism notfreshpopulationholdout.','ROOTfamilies freshD4/color-disjoint1672, samebalancedrole law and native-opponent objective replication.').replace('noUNKNOWN inthese4096episodes.','UNKNOWN retained if horizon128 reached; cycles only specific cached full-state policies.')
(O/'audit.py').write_text(s,encoding='utf8')
for p in O.glob('*.py'):ast.parse(p.read_text());print(p,hashlib.sha256(p.read_bytes()).hexdigest())
priv=R/'.local_agent/slack'; raw=''.join(p.read_text(encoding='utf-8-sig').rstrip('\n') for p in sorted(priv.glob('start52-*.raw'))); obj=json.loads(raw);(priv/'start52.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
