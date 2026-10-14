from pathlib import Path
import json,ast
R=Path.cwd();O=R/'results/dev_aux/task1438';d=json.loads((R/'results/dev_aux/task1402/train_manifest.json').read_bytes())
d.update(root_range=[0,8],root_count=8,profiles={k:d['profiles'][k] for k in ['R720B720','R1728B720']},expected_games=56,expected_logical_games=64,compress_identical_selfplay=True,max_seconds=120,expected_seconds=15,scope='Engineeringcontrolonly first8 oldTRAIN atsameseeds/budget/RNG/binary. Existing64dualactual referencecase data preserved. 56NEWphysical/64logical, onlyidenticalunitselfplaycompress8. Random/nonnativeequalexcluded. No new independent scienceorretroactivecostreduction.')
(O/'manifest.json').write_text(json.dumps(d,indent=2));ast.parse((O/'runner.py').read_text(encoding='utf-8-sig'));print('FROZEN_DEDUP_CONTROL56physical64logical')
