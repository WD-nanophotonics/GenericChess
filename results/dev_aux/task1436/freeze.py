from pathlib import Path
import json,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1436';base=json.loads((R/'results/dev_aux/task1402/train_manifest.json').read_bytes());p=json.loads((R/'results/dev_aux/task1430/study.json').read_bytes())
base.update(H=48,nodes=512,max_seconds=400,expected_seconds=100,root_file=p['root_file'],root_sha256=hashlib.sha256((R/p['root_file']).read_bytes()).hexdigest(),root_range=[0,32],root_count=32,expected_games=2048,random_seed_base=p['random_seed_base'],scope='Canonicalonly actualTRAIN32/H48/512nodes, newfreshμsamepriceblindscope; task1432/plan.json inheritedgenerator metadata notscientific/runtimeauthority, task1430study governs. NoDEVfit; high/lowDEVfrozenbeforeoutcomes.')
(O/'train_manifest.json').write_text(json.dumps(base,indent=2))
