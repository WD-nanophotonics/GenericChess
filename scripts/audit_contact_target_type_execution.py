"""Qualify the zero-observation initial envelope without altering old evidence."""
from dataclasses import replace
import hashlib,json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from scripts.audit_contact_target_type_falsifier import build
SOURCE=ROOT/'scripts/audit_contact_target_type_falsifier.py'
def qualified_build(guarded):
    r=build(guarded)
    return replace(r,piece_types=tuple(replace(p,movement=(LeapAtom((0,1)),)) if p.type_id=='K' else p for p in r.piece_types))
if __name__=='__main__':
    old=json.loads((ROOT/'docs/research/data/contact_target_type_falsifier_20261005.json').read_text())
    assert not old['complete'] and old['enumerated']==old['public_transitions']==old['candidates']==0
    target=ROOT/'docs/research/data/contact_target_type_execution_20261005.json'
    if target.exists():raise FileExistsError('frozen qualified guard audit')
    code=SOURCE.read_text()
    code=code.replace("OUT=ROOT/'docs/research/data/contact_target_type_falsifier_20261005.json'","OUT=ROOT/'docs/research/data/contact_target_type_execution_20261005.json'")
    code=code.replace("SOURCES=('scripts/audit_contact_target_type_falsifier.py',","SOURCES=('scripts/audit_contact_target_type_execution.py','docs/research/CONTACT_TARGET_TYPE_EXECUTION_SCOPE.md','docs/research/data/contact_target_type_falsifier_20261005.json','scripts/audit_contact_target_type_falsifier.py',")
    code=code.replace('c=compile_ruleset_for_execution(build(guarded))','c=compile_ruleset_for_execution(qualified_build(guarded))')
    exec(compile(code,str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE),'qualified_build':qualified_build})
