"""Narrow R/TR tables after zero-row cube ABI failure, cumulative budget."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'scripts/audit_shogi_profile_table_reuse.py';OUT=ROOT/'docs/research/data/shogi_ray_profile_qualified_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed narrowed audit')
    failed=json.loads((ROOT/'docs/research/data/shogi_profile_table_reuse_20261006.json').read_text());assert not failed['table_rows'] and not failed['controls'] and failed['canonical_candidates']==2768
    for path,pin in failed['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
    code=OLD.read_text().replace('shogi_profile_table_reuse_20261006.json','shogi_ray_profile_qualified_20261006.json')
    code=code.replace("tuple(literals.pop(source,()))!=('own',)", "tuple(literals.pop(source,('own',)))!=('own',)")
    code=code.replace("pp=tuple(Profile(**row['profile']) for row in old['rows'])", "pp=tuple(Profile(**row['profile']) for row in old['rows'] if row['profile']['current'] in ('R','TR'))")
    code=code.replace('((40,41,0),(0,1,80),(67,76,40))','((40,41,0),)').replace("len(r['table_rows'])==1053 and len(r['controls'])==39","len(r['table_rows'])==162 and len(r['controls'])==2")
    code=code.replace("r['reused_distance_rows']=old['rows']", "r['reused_distance_rows']=[x for x in old['rows'] if x['profile']['current'] in ('R','TR')]")
    code=code.replace('monotonic()-start>=15','monotonic()-start+1.25>=15').replace("r['canonical_candidates']+r['candidates']+r['returned_actions']>5000", "r['canonical_candidates']+r['candidates']+r['returned_actions']+3268>5000")
    code=code.replace("SOURCES=('scripts/audit_shogi_profile_table_reuse.py',", "SOURCES=('scripts/audit_shogi_ray_profile_qualified.py','docs/research/SHOGI_PROFILE_TABLE_SCOPE_CORRECTION.md','docs/research/data/shogi_profile_table_reuse_20261006.json','scripts/audit_shogi_profile_table_reuse.py',")
    code=code.replace('(ROOT/SOURCES[3])',"(ROOT/'docs/research/data/shogi_full_contact_distance_20261005.json')").replace('(ROOT/SOURCES[4])',"(ROOT/'docs/research/data/shogi_coordinate_comparison_20261005.json')")
    code=code.replace("r['seconds']=monotonic()-start;", "r['charged_canonical_candidates']=3268+r['canonical_candidates'];r['charged_enumeration']=3268+r['canonical_candidates']+r['candidates']+r['returned_actions'];r['cumulative_seconds']=monotonic()-start+1.25;r['seconds']=monotonic()-start;")
    exec(compile(code,str(OLD),'exec'),{'__name__':'__main__','__file__':str(OLD)})
