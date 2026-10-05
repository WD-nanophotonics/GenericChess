"""Grouped atom-source counterexample, immutable failures and corrected view."""
import hashlib,json
from pathlib import Path
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.typed_sparse_contact_cubes import TypedSparseContactCubes
from scripts.shared_contact_prefix import Profile
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/data'


def test_actor_binding_disambiguation_is_necessary_and_matches_both_owners():
    r=json.loads((DATA/'contact_typed_geometry_valid_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==8 and r['old_mismatches']==4
    assert r['canonical_candidates']==48 and r['enumerated']==16 and r['seconds']<15
    assert r['public_transitions']==r['virtual_materializations']==r['goal_queries']==0
    for row in r['rows']:
        assert row['actual']==row['typed_direct']
        expected=(row['type']=='X' and row['target'] in (3,5)) or (row['type']=='Y' and row['target'] in (1,7))
        assert row['actual']==expected
    assert any(len(p['type_ids'])==2 for p in r['compiled_patterns'])


def test_compile_rejections_are_preserved_as_zero_observation_not_executed_retries():
    for name,reason in (('contact_typed_geometry_20261005.json','ANCHOR_COUNT'),
                        ('contact_typed_geometry_anchored_20261005.json','DROP_MASK_INVALID_SET')):
        r=json.loads((DATA/name).read_text());assert not r['complete'] and reason in r['error']
        assert r['enumerated']==r['canonical_candidates']==0
    for name in ('contact_typed_geometry_20261005.json','contact_typed_geometry_anchored_20261005.json','contact_typed_geometry_valid_20261005.json'):
        r=json.loads((DATA/name).read_text());assert r['source_hashes_unchanged']
        for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_type_bound_view_preserves_saved_single_type_screen_leg_eye_zone_controls():
    raw=json.loads((DATA/'sparse_contact_cube_controls_20261005.json').read_text())
    c=compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset())
    kernel=TypedSparseContactCubes(c,tuple(Profile(t,t) for t in 'ACEHRS'))
    assert kernel.c is c and kernel.stats['canonical_candidates']==2791
    for row in raw['rows']:
        if row['owner']:continue
        t=row['position']['board'][row['source']]['current_type_id']
        assert kernel.pair_success(Profile(t,t),row['source'],row['target'])==(row['first_mask'],row['second_mask'])
