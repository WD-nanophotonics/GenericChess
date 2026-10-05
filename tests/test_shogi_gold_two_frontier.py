"""Independent blocked-coordinate frontier and Pawn/Gold coupling controls."""
import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
from scripts.gold_two_frontier import gold_two_counts,gold_partial_interval
from scripts.shogi_direct_mode_bounds import TOTAL,LEAPS
from tests.test_shogi_direct_mode_bounds import targets

ROOT=Path(__file__).resolve().parents[1]


def test_two_step_coordinate_union_independent_of_intersections():
    for owner in (0,1):
        first_mass=second_mass=0
        for s in range(81):
            for b in range(81):
                if b==s:
                    continue
                first=targets('G',s,owner,b)
                second=set().union(*(targets('G',u,owner,b) for u in first))
                second.discard(s);second.difference_update(first)
                first_mass+=len(first);second_mass+=len(second)
        count=gold_two_counts()
        assert (first_mass,second_mass)==(count['direct'],count['second'])==(32864,55171)


def test_saved_source_pins_and_remaining_mass():
    r=json.loads((ROOT/'docs/research/data/gold_two_frontier_20261005.json').read_text(encoding='utf-8'))
    assert r['complete'] and r['seconds']<15 and r['source_hashes_unchanged']
    assert r['public_transitions']==r['goal_queries']==0
    assert r['direct']+r['second']+r['remaining']==TOTAL
    assert r['nondirect_pair_multiplicity']=={'0':5362,'1':287,'2':366,'3':49}
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for m,pair in r['raw_intervals'].items():
        assert tuple(F(v) for v in pair)==gold_partial_interval(m)


def test_pawn_paths_can_be_coupled_into_current_gold_without_adding_steps():
    # Before native P promotion its sole displacement is a Gold displacement;
    # afterwards TP and Gold share the same qualified grammar. Occupancy is identical.
    assert set(LEAPS['P']) <= set(LEAPS['TP']) == set(LEAPS['G'])
    extra=0
    for owner in (0,1):
        mass=0
        for s in range(81):
            for b in range(81):
                if s==b:
                    continue
                p=targets('P',s,owner,b);g=targets('TP',s,owner,b)
                assert p<=g
                mass+=len(g-p)
        assert mass==32864-5688==27176
        extra+=mass
    assert extra==2*27176
    assert F(27176,TOTAL)*(F(1,2)-F(1,4))==F(3397,255960)
    assert F(27176,TOTAL)*(F(1,3)-F(1,6))==F(3397,383940)
