"""Independent definite occupancy replay of saved fresh physical events."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shared_prefix_events_20261005.json'


def test_frozen_physical_qualification_budget_and_hashes():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    assert r['complete'] and 'error' not in r and r['source_hashes_unchanged']
    assert (r['materializations'],r['geometry_candidates'])==(42,256)
    assert r['seconds']<15 and r['public_transitions']==r['goal_queries']==0
    assert len(r['rows'])==4 and all(x['complete'] for x in r['rows'])
    assert all(t['complete'] and t['excluded_dynamic']=='own_anchor_safe' for t in r['tables'])
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_complete_silver_first_options_and_unique_promoted_capture():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    for row in r['rows']:
        if row['kind']!='Silver2':continue
        assert len(row['first'])==6 and len(row['removals'])==1
        assert {x['node']['current'] for x in row['first']}=={'S','TS'}
        for x in row['first']:
            assert x['node']['base']=='S'
        route=row['removals'][0]
        assert route['first'][6]=='TS' and route['last'][1]=='TS'
        assert route['last'][5]==[[row['target'],'capture_to_hand']]
        assert route['node']['base']=='S' and route['node']['current']=='TS'
        sign=1 if row['owner']==0 else -1
        first,last=route['first'],route['last']
        assert ((first[3]%9-first[2]%9)*sign,(first[3]//9-first[2]//9)*sign)==(1,1)
        assert ((last[3]%9-last[2]%9)*sign,(last[3]//9-last[2]//9)*sign)==(1,0)


def test_rook_final_cube_requires_vacated_original_source():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    for row in r['rows']:
        if row['kind']!='RookVacating':continue
        table=next(t for t in r['tables'] if t['owner']==row['owner'] and
                   t['node']==dict(base='R',current='R',square=row['intermediate']))
        packet=next(x for x in table['events'] if x['event']==row['last'])
        occupied={row['intermediate']:'own',row['blocker']:'own',row['target']:'enemy'}
        matches=lambda cube,world:all(world.get(s,'empty') in labels for s,labels in cube)
        assert any(matches(cube,occupied) for cube in packet['cubes'])
        assert not any(matches(cube,{**occupied,row['source']:'own'}) for cube in packet['cubes'])
        assert any([row['source'],['empty']] in cube for cube in packet['cubes'])
