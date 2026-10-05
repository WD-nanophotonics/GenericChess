"""Coordinate controls and saved metadata, no whole-board event producer."""
import hashlib
import json
from pathlib import Path
import pytest
from scripts.shogi_direct_mode_bounds import LEAPS,RAYS,TOTAL,direct_and_zero,partial_raw_interval

ROOT=Path(__file__).resolve().parents[1]


def targets(tid, source, owner, blocker=None):
    x,y=source%9,source//9; sign=1 if owner==0 else -1
    found=set()
    for dx,dy in LEAPS[tid]:
        a,b=x+sign*dx,y+sign*dy
        if 0<=a<9 and 0<=b<9 and b*9+a!=blocker:
            found.add(b*9+a)
    for dx,dy in RAYS.get(tid,()):
        for k in range(1,9):
            a,b=x+sign*dx*k,y+sign*dy*k
            if not (0<=a<9 and 0<=b<9) or b*9+a==blocker:
                break
            found.add(b*9+a)
    return found


@pytest.mark.parametrize('tid',list(LEAPS))
def test_coordinate_direct_mass_and_motionless_zero_for_both_owners(tid):
    for owner in (0,1):
        direct=zero=0
        for source in range(81):
            for blocker in range(81):
                if blocker==source:
                    continue
                reachable=targets(tid,source,owner,blocker)
                direct+=len(reachable)
                if not reachable:
                    zero+=79  # Every distinct ordinary target world is immobile.
        assert (direct,zero)==direct_and_zero(tid)
        assert sum((direct,zero,TOTAL-direct-zero))==TOTAL


def test_promoted_gold_direct_equality_is_not_native_pre_promotion_equality():
    assert all(direct_and_zero(t)==direct_and_zero('G') for t in ('TP','TL','TN','TS'))
    assert direct_and_zero('P')!=direct_and_zero('TP')
    assert direct_and_zero('N')!=direct_and_zero('TN')
    assert direct_and_zero('S')!=direct_and_zero('TS')
    assert targets('S',72,0,64)==set() and targets('TS',72,0,64)


def test_raw_partial_bounds_keep_mass_without_unknown_max_normalization():
    for tid in LEAPS:
        for duration in ('geometric_half','linear_mixture'):
            lo,hi=partial_raw_interval(tid,duration)
            assert 0<lo<hi<1
    with pytest.raises(ValueError):
        partial_raw_interval('K','geometric_half')
    with pytest.raises(ValueError):
        partial_raw_interval('P','tuned')


def test_failed_and_corrected_qualification_are_both_preserved():
    failed=json.loads((ROOT/'docs/research/data/shogi_direct_modes_20261005.json').read_text(encoding='utf-8'))
    good=json.loads((ROOT/'docs/research/data/shogi_direct_modes_correction_20261005.json').read_text(encoding='utf-8'))
    assert not failed['complete'] and failed['checked_patterns']==1 and not failed['modes']
    assert 'unsupported state/history/postcondition' in failed['error']
    assert good['complete'] and good['checked_patterns']==110 and len(good['modes'])==11
    for r in (failed,good):
        assert r['seconds']<15 and r['source_hashes_unchanged']
        assert all(r[k]==0 for k in ('public_transitions','goal_queries','geometry_candidates','event_materializations'))
        for p,h in r['source_sha256'].items():
            assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for tid,row in good['modes'].items():
        assert (row['direct'],row['proved_zero'])==direct_and_zero(tid)
        assert row['excluded_dynamic']=='own_anchor_safe'


def test_inherited_promotion_masks_have_live_outputs_for_every_allowed_pair():
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    for base in ('P','L','N','S','B','R'):
        meta=c.support.type_metadata[base]
        for owner in (0,1):
            allowed=c.support.promotion_allowed[base][owner]
            forced=c.support.promotion_forced[base][owner]
            for source,destination in allowed:
                idx=destination.rank*9+destination.file
                assert any(c.support.empty_mobility[t][owner][idx] for t in meta.promotion_target_ids)
                if destination in forced:
                    assert not c.support.empty_mobility[base][owner][idx]
            for tid in ('TP','TL','TN','TS','TB','TR'):
                assert all(c.support.empty_mobility[tid][owner][i] for i in range(81))
