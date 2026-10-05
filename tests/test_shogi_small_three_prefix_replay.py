"""Independent coordinate frontiers, both owners, not shared-kernel replay."""
import hashlib,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shogi_small_three_prefix_20261005.json'
ATOMS={'S':((0,1),(-1,1),(1,1),(-1,-1),(1,-1)),
 'N':((-1,2),(1,2)), 'G':((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1))}


def neighbors(mode,s,b,owner):
    sign=1 if owner==0 else -1
    for dx,dy in ATOMS[mode]:
        x,y=s%9+dx*sign,s//9+dy*sign
        if 0<=x<9 and 0<=y<9 and y*9+x!=b:yield y*9+x


@pytest.mark.parametrize('native',['S','N','G'])
def test_full_three_action_coordinate_union_both_owners(native):
    raw=json.loads(RAW.read_text());r=next(x for x in raw['rows'] if x['profile']['current']==native)
    for owner in (0,1):
        counts=[0,0,0];rank=lambda u:u//9 if owner==0 else 8-u//9
        for s in range(81):
            for b in range(81):
                if s==b:continue
                frontier={(native,s)};seen={s}
                for step in range(3):
                    nxt=set();targets=set()
                    for mode,u in frontier:
                        for v in neighbors(mode,u,b,owner):
                            targets.add(v)
                            promote=mode!='G' and (rank(u)>=6 or rank(v)>=6)
                            if not (mode=='N' and rank(v)>=7):nxt.add((mode,v))
                            if promote:nxt.add(('G',v))
                    counts[step]+=len(targets-seen);seen|=targets;frontier=nxt
        assert tuple(counts)==(r['direct'],r['second'],r['third'])


def test_frozen_complete_cost_and_mass():
    r=json.loads(RAW.read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and r['seconds']<15
    assert r['public_transitions']==r['goal_queries']==r['event_materializations']==0
    assert r['preprocessing']['geometry_candidates']==656
    for row in r['rows']:assert sum(row[k] for k in ('direct','second','third','remaining'))==511920
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
