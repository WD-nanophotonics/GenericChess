"""Actual compiled metadata name; frozen real-Shogi experiment unchanged."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'scripts/audit_shogi_promotion_cubes.py'
if __name__=='__main__':
    old=json.loads((ROOT/'docs/research/data/shogi_promotion_cubes_20261005.json').read_text())
    assert old['worlds']==old['canonical_candidates']==0 and old['error']=='AttributeError: fingerprint'
    code=SOURCE.read_text().replace("OUT=ROOT/'docs/research/data/shogi_promotion_cubes_20261005.json'","OUT=ROOT/'docs/research/data/shogi_promotion_qualified_20261005.json'")
    code=code.replace('compiled.fingerprint','compiled.ruleset_fingerprint').replace('monotonic()-start>=15','monotonic()-start+0.109>=15')
    code=code.replace("SOURCES=('scripts/audit_shogi_promotion_cubes.py',","SOURCES=('scripts/audit_shogi_promotion_qualified.py','docs/research/SHOGI_PROMOTION_METADATA_SCOPE.md','docs/research/data/shogi_promotion_cubes_20261005.json','scripts/audit_shogi_promotion_cubes.py',")
    code=code.replace("r['seconds']=monotonic()-start;","r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.109;")
    exec(compile(code,str(SOURCE),'exec'),{'__name__':'__main__','__file__':str(SOURCE)})
