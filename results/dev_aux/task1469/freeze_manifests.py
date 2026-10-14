from pathlib import Path
import json,hashlib,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1473';root=R/'results/dev_aux/task1470/roots.json';d=json.loads((R/'results/dev_aux/task1460/manifest.json').read_bytes());rows=[]
for group,slice_ in [('early',[0,16]),('late',[48,64])]:
 p=dict(d,root_file=str(root.relative_to(R)),root_sha256=hashlib.sha256(root.read_bytes()).hexdigest(),root_range=slice_,random_seed_base=2026579000,scope=f'Nextsegment actualTRAIN16 {group}pawnμ only, all32freshDEVofgroupuntouched. FixedH48/1024/nativePNBR720,R1728/N,B720,Pgrid4; fullpromotion/EP, nohumanfit. Onlycanonicalmax_seconds180, no replayoldPfail.')
 path=O/f'train_{group}.json';path.write_text(json.dumps(p,indent=2))
 sp=importlib.util.spec_from_file_location('scopedP',R/'results/dev_aux/task1460/runner.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);rr=m.validate(p);assert len(rr)==16 and all(x['group']==group and x['phase']=='TRAIN' for x in rr)
 rows.append(dict(group=group,root_count=16,manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),new_go=0))
(O/'qualification.json').write_text(json.dumps(dict(status='PASS_FUTURE_EARLY_LATE_CANONICAL_TRAIN_MANIFESTS_NO_GAMES',rows=rows),indent=2));print(rows)
