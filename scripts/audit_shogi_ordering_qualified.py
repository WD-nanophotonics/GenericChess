"""Correct zero-search dependency-index shift; preserve original evidence."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'scripts/audit_shogi_ordering_cost.py';OUT=ROOT/'docs/research/data/shogi_ordering_qualified_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('one qualified intervention')
    failed=json.loads((ROOT/'docs/research/data/shogi_ordering_cost_20261006.json').read_text())
    assert failed['runtime_pushes']==failed['candidates']==failed['returned_actions']==0 and failed['error'].startswith('AssertionError')
    code=OLD.read_text().replace('shogi_ordering_cost_20261006.json','shogi_ordering_qualified_20261006.json')
    insertion="    code=code.replace('(ROOT/SOURCES[3])', \"(ROOT/'docs/research/data/shogi_promotion_use_20261005.json')\")\n    code=code.replace(\"SOURCES=('scripts/audit_shogi_ordering_cost.py',\", \"SOURCES=('scripts/audit_shogi_ordering_qualified.py','docs/research/SHOGI_ORDERING_INPUT_SCOPE.md','docs/research/data/shogi_ordering_cost_20261006.json','scripts/audit_shogi_ordering_cost.py',\")\n"
    code=code.replace('    exec(compile(code',insertion+'    exec(compile(code')
    exec(compile(code,str(OLD),'exec'),{'__name__':'__main__','__file__':str(OLD)})
