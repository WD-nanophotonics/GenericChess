"""Correct actual PieceType field; preserve both zero-observation failures."""
from dataclasses import replace
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from scripts.audit_contact_target_type_falsifier import build
SOURCE=ROOT/'scripts/audit_contact_target_type_falsifier.py'
def qualified_build(guarded):
    r=build(guarded)
    return replace(r,piece_types=tuple(replace(p,movement_atoms=(LeapAtom((0,1)),)) if p.type_id=='K' else p for p in r.piece_types))
if __name__=='__main__':
    for name in ('contact_target_type_falsifier','contact_target_type_execution'):
        old=json.loads((ROOT/f'docs/research/data/{name}_20261005.json').read_text())
        assert not old['complete'] and old['enumerated']==old['public_transitions']==old['candidates']==0
    target=ROOT/'docs/research/data/contact_target_type_qualified_20261005.json'
    if target.exists():raise FileExistsError('frozen guarded audit')
    code=SOURCE.read_text().replace("OUT=ROOT/'docs/research/data/contact_target_type_falsifier_20261005.json'","OUT=ROOT/'docs/research/data/contact_target_type_qualified_20261005.json'")
    code=code.replace("SOURCES=('scripts/audit_contact_target_type_falsifier.py',","SOURCES=('scripts/audit_contact_target_type_qualified.py','generic_chess/core/pieces.py','docs/research/CONTACT_TARGET_TYPE_QUALIFIED_SCOPE.md','scripts/audit_contact_target_type_execution.py','docs/research/data/contact_target_type_execution_20261005.json','docs/research/CONTACT_TARGET_TYPE_EXECUTION_SCOPE.md','docs/research/data/contact_target_type_falsifier_20261005.json','scripts/audit_contact_target_type_falsifier.py',")
    code=code.replace('c=compile_ruleset_for_execution(build(guarded))','c=compile_ruleset_for_execution(qualified_build(guarded))')
    exec(compile(code,str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE),'qualified_build':qualified_build})
