"""Behavioral cube projection and sparse intrinsic mechanics, no new labels."""
from fractions import Fraction
from itertools import product
import hashlib,json
from pathlib import Path
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix
from scripts.sparse_contact_cubes import SparseContactCubes,blocker_mask
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/sparse_contact_cube_controls_20261005.json'


def test_cube_projection_matches_exhaustive_single_blocker_assignments():
    labelsets=(('empty',),('own',),('enemy',),('empty','own'),('empty','enemy'),('own','enemy'))
    for labels in product(labelsets,repeat=3):
        cube=tuple(zip((0,2,4),labels))
        for target in (2,3):
            actual=blocker_mask(cube,area=6,source=0,target=target,enemy=2)
            expected=0
            for blocker in range(6):
                if blocker in (0,2) or (target!=2 and blocker==target):continue
                occupancy=lambda q:'own' if q in (0,blocker) else 'enemy' if q==2 else 'empty'
                if all(occupancy(q) in allowed for q,allowed in cube):expected|=1<<blocker
            assert actual==expected


def test_saved_screen_leg_eye_zone_and_owner_controls():
    r=json.loads(RAW.read_text());assert r['complete'] and len(r['rows'])==24
    assert r['canonical_candidates']==2791 and r['enumerated']==188
    assert r['seconds']<15 and r['goal_queries']==r['public_transitions']==0
    assert r['human_reference_imported'] is False
    for row in r['rows']:
        actual=any(a['source']==row['source'] and a['target']==row['target'] for a in row['all_actions'])
        assert actual==row['direct']
        if row['owner']==0:
            bit=1<<row['blocker']
            assert bool(row['first_mask']&bit)==row['direct']
            assert bool(row['second_mask']&bit)==row['second']
            assert row['first_mask']&row['second_mask']==0
    route=r['routes'];assert len(route)==r['virtual_materializations']==2
    for step in route:assert step['action'] in step['all_actions'] and step['raw_after']['side_to_move']==1
    assert route[0]['raw_after']['board'][27]['base_type_id']=='C'
    assert route[1]['raw_after']['board'][30]['base_type_id']=='C'
    assert route[1]['raw_after']['board'][28]['base_type_id']=='A'
    assert route[1]['raw_after']['board'][27] is None


def test_promotion_origin_and_source_vacating_agree_with_qualified_simple_kernel():
    c=compile_ruleset_for_execution(build_standard_shogi_ruleset())
    profiles=tuple(Profile(t,t) for t in ('P','N','S'))
    cube=SparseContactCubes(c,profiles);simple=SharedContactPrefix(c,profiles)
    # Selected parity, promotion-zone and vacated-source controls; no population rerun.
    for p in profiles:
        for s,d in ((0,1),(40,60),(49,68),(60,70),(72,80)):
            assert cube.pair_success(p,s,d)==simple.pair_success(p,s,d)


def test_auxiliary_profile_is_rejected_whole_not_silently_filtered():
    c=compile_ruleset_for_execution(build_western_chess_ruleset())
    with pytest.raises(ValueError,match='compound/auxiliary'):
        SparseContactCubes(c,(Profile('P','P'),))


def test_frozen_cube_inputs_match_without_producer_reexecution():
    r=json.loads(RAW.read_text());assert r['source_hashes_unchanged']
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
