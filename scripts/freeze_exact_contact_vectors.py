"""Freeze exact rational candidates, not official model admission."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.shogi_exact_twenty_family import exact_twenty_intervals
OUT=ROOT/'docs/research/data/exact_contact_vectors_20261005.json'
SOURCES=('scripts/freeze_exact_contact_vectors.py','docs/research/EXACT_CONTACT_VECTOR_FREEZE_PROTOCOL.md',
 'scripts/chess_exact_contact_family.py','scripts/shogi_exact_twenty_family.py','scripts/shogi_exact_contact_family.py',
 'docs/research/data/chess_zero_target_correction_20261005.json','docs/research/data/shogi_coordinate_comparison_20261005.json',
 'docs/research/data/shogi_exact_held_reweight_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen vectors')
    vectors={}
    for law in ('geometric_half','linear_mixture'):
        vectors[law]={}
        for game,fn,scale in (('chess',exact_chess_contact_intervals,'Q'),('shogi',exact_twenty_intervals,'TR')):
            entries=fn(law);assert all(lo==hi for lo,hi in entries.values())
            vectors[law][game]=dict(common_maximum=scale,weights={kind+':'+mode:str(lo) for (kind,mode),(lo,hi) in entries.items()})
    r=dict(complete=True,admitted_official_prior=False,public_transitions=0,source_queries=0,vectors=vectors,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(complete=True,laws=2,chess_modes=5,shogi_modes=20)))
