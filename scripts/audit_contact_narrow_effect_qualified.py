"""Preserve failed producer; qualify its public metadata field only."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/audit_contact_narrow_effect_certificate.py').read_text()
assert source.count('state.ply')==2
source=source.replace('state.ply','state.ply_count')
source=source.replace("OUT=ROOT/'docs/research/data/contact_narrow_effect_certificate_20261005.json'","OUT=ROOT/'docs/research/data/contact_narrow_effect_qualified_20261005.json'")
source=source.replace("if __name__=='__main__':","SOURCES+=('scripts/audit_contact_narrow_effect_qualified.py','docs/research/CONTACT_NARROW_EFFECT_METADATA_SCOPE.md','docs/research/data/contact_narrow_effect_certificate_20261005.json')\nif __name__=='__main__':")
exec(compile(source,str(ROOT/'scripts/audit_contact_narrow_effect_certificate.py'),'exec'))
