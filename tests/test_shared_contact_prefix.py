"""Saved prefix, independent Silver geometry and qualified-cache boundaries."""
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import pytest
from generic_chess.core.coordinates import Square
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import Profile,SharedContactPrefix

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shared_contact_prefix_shogi_20261005.json'
SILVER=((0,1),(-1,1),(1,1),(-1,-1),(1,-1))
GOLD=((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))


def neighbors(s,atoms,owner,b):
    x,y=s%9,s//9;sign=1 if owner==0 else -1
    return {9*(y+sign*dy)+x+sign*dx for dx,dy in atoms
            if 0<=x+sign*dx<9 and 0<=y+sign*dy<9 and 9*(y+sign*dy)+x+sign*dx!=b}


def test_independent_silver_two_action_target_union_both_owners():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    saved=next(x for x in r['rows'] if x['profile']['current']=='S')
    for owner in (0,1):
        first=second=unpromoted_second=0;zone={6,7,8} if owner==0 else {0,1,2}
        for s in range(81):
            for b in range(81):
                if b==s:continue
                direct=neighbors(s,SILVER,owner,b);future=set();native=set()
                for u in direct:
                    native|=neighbors(u,SILVER,owner,b)
                    future|=neighbors(u,SILVER,owner,b)
                    if s//9 in zone or u//9 in zone:future|=neighbors(u,GOLD,owner,b)
                native-=direct|{s};future-=direct|{s}
                first+=len(direct);second+=len(future);unpromoted_second+=len(native)
        assert (first,second)==(saved['direct'],saved['second'])==(25912,67769)
        assert unpromoted_second<second  # Optional quiet promotion changes this frontier.


def test_saved_earlier_frontiers_and_cost_improvement():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    assert r['complete'] and r['seconds']<15 and r['source_hashes_unchanged']
    assert r['public_transitions']==r['goal_queries']==r['event_materializations']==0
    p=r['preprocessing']
    assert (p['checked_patterns'],p['raw_pattern_candidates'],p['geometry_candidates'])==(126,15368,2768)
    assert p['source_geometry_tables']==1458 and p['canonical_geometries']==18
    assert p['max_quiet_variants']<=128 and len(r['rows'])==13
    rows={x['profile']['current']:x for x in r['rows']}
    assert (rows['P']['direct'],rows['P']['second'])==(5688,11154)
    assert all((rows[t]['direct'],rows[t]['second'])==(32864,55171) for t in ('G','TP','TL','TN','TS'))
    assert (rows['R']['direct'],rows['R']['second'],rows['R']['remaining'])==(99360,409536,3024)
    assert all(x['direct']+x['second']+x['remaining']==x['total']==511920 for x in r['rows'])
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_owner_reflection_of_every_compiled_path_and_promotion_mask():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    for g in c.ir.geometry.values():
        if g.kind=='drop':continue
        for s in range(81):
            assert g.paths['1'][s]==tuple(80-x for x in g.paths['0'][80-s])
    mirror=lambda q:Square(8-q.file,8-q.rank)
    for base in ('P','L','N','S','B','R'):
        a=c.support.promotion_allowed[base]
        f=c.support.promotion_forced[base]
        assert a[1]==frozenset((mirror(s),mirror(d)) for s,d in a[0])
        assert f[1]==frozenset(mirror(q) for q in f[0])


def test_silver_optional_promotion_only_pair_and_original_source_vacates():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    p=Profile('S','S');k=SharedContactPrefix(c,[p])
    first,second=k.pair_success(p,54,65)  # a7 -> b8 promoted -> c8.
    assert first==0 and second&(1<<0)
    # Gold a1->b1->a2: original source may be on a second movement path, never a blocker.
    g=Profile('G','G');gold=SharedContactPrefix(c,[g])
    a,b=gold.pair_success(g,0,9)
    assert a & (1<<80)  # Direct contacts are removed from exact-two, not counted twice.
    assert not b & (1<<80)


def test_unknown_board_guard_and_invalid_origin_reject_whole_requested_set():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    with pytest.raises(ValueError,match='promotion/origin'):
        SharedContactPrefix(c,[Profile('N','TN',False)])
    patterns=list(c.ir.patterns)
    i=next(i for i,p in enumerate(patterns) if 'S' in p.type_ids and p.target.kind=='target_empty')
    patterns[i]=replace(patterns[i],slot_guards=('unsupported',))
    changed=replace(c,ir=replace(c.ir,patterns=tuple(patterns)))
    with pytest.raises(ValueError,match='unsupported state'):
        SharedContactPrefix(changed,[Profile('G','G'),Profile('S','S')])
