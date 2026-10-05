import hashlib,json
from pathlib import Path
from scripts.audit_shogi_profile_table_reuse import coordinate_edges
from scripts.shared_contact_prefix import Profile
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_independent_ray_paths_promotion_and_dragon_extra_steps():
    native=list(coordinate_edges(Profile('R','R'),40));dragon=list(coordinate_edges(Profile('R','TR',True),40))
    assert (42,Profile('R','R'),1<<41) in native
    assert (67,Profile('R','TR',True),(1<<49)|(1<<58)) in native
    assert (50,Profile('R','TR',True),0) in dragon
    assert all(q==Profile('R','TR',True) for d,q,path in dragon)

def test_whole_narrowed_edge_identity_and_cumulative_caps():
    failed=json.loads((DATA/'shogi_profile_table_reuse_20261006.json').read_text());r=json.loads((DATA/'shogi_ray_profile_qualified_20261006.json').read_text())
    assert not failed['table_rows'] and not failed['controls'] and failed['canonical_candidates']==2768
    assert r['complete'] and len(r['table_rows'])==162 and all(x['match'] for x in r['table_rows'])
    assert len(r['controls'])==2 and all(x['actual']==x['coordinate'] for x in r['controls'])
    assert r['charged_enumeration']==4899 and r['cumulative_seconds']<15 and r['distance_worlds']==0
    assert r['public_transitions']==r['source_queries']==0
    assert {x['profile']['current'] for x in r['reused_distance_rows']}=={'R','TR'}
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
