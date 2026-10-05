"""Preserve compiler-envelope failure; observations run only in qualified layer."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/audit_promotable_cube_micro.py').read_text()
source=source.replace("OUT=ROOT/'docs/research/data/promotable_cube_micro_20261005.json'","OUT=ROOT/'docs/research/data/promotable_cube_qualified_20261005.json'")
source=source.replace('a.promotion_type','a.promotion_target_id')
source=source.replace("if __name__=='__main__':","from scripts.promotable_micro_qualified import qualified_build\nbuild=qualified_build\nSOURCES+=('scripts/audit_promotable_cube_qualified.py','scripts/promotable_micro_qualified.py','docs/research/PROMOTABLE_CUBE_ENVELOPE_SCOPE.md','docs/research/data/promotable_cube_micro_20261005.json')\nif __name__=='__main__':")
source=source.replace('monotonic()-start>=15','monotonic()-start+0.016>=15')
source=source.replace("r['seconds']=monotonic()-start;","r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.016;")
exec(compile(source,str(ROOT/'scripts/audit_promotable_cube_micro.py'),'exec'))
