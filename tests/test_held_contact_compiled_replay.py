"""Independent saved-path checks; never rerun the frozen event producer."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def report():
    return json.loads((ROOT/'docs/research/data/held_contact_compiled_20261005.json').read_text())


def test_frozen_report_budget_and_sources():
    r=report()
    assert r['complete'] and r['source_hashes_unchanged'] and 'error' not in r
    assert r['materializations']==28 and r['geometry_candidates']==384
    assert r['scope']==dict(n=1,virtual=True,public_transitions=0,goal_calls=0,
                           royal_safety=False,opponent_turns=False,full_inventory=False)
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for tid,t in r['drop_tables'].items():
        assert t['target_count']==162 and not t['excluded_state_constraints']
        assert t['excluded_dynamic']==[[f'legacy_{tid}_drop','own_anchor_safe']]
        assert t['coarse_coverage_complete'] and not t['full_legality_modeled']
        assert {(x['key'][0],x['key'][3]) for x in t['events']}=={
            (owner,sq) for owner in (0,1) for sq in range(81)}


def test_saved_selected_paths_replay_definite_occupancy_and_type_identity():
    r=report()
    for row in r['routes']:
        source=None;current=row['base'];d=row['target'];b=row['blocker']
        for index,step in enumerate(row['steps']):
            e=step['event'];destination=e[3]
            occupancy={d:'enemy',b:'own'}
            if source is not None:
                occupancy[source]='own'
            assert any(all(occupancy.get(sq,'empty') in allowed for sq,allowed in cube)
                       for cube in step['cubes'])
            assert e[0]==row['owner'] and e[1]==current
            if index==0:
                assert e[2]=='hand' and not e[5] and e[6]==row['base']
            else:
                assert e[2]==source
                x,y=source%9,source//9;u,v=destination%9,destination//9
                dx,dy=abs(u-x),abs(v-y)
                if current=='B':
                    assert dx==dy>0
                    assert e[6]=='TB'
                    zone={6,7,8} if row['owner']==0 else {0,1,2}
                    assert y in zone or v in zone
                elif current=='TB':
                    assert dx+dy==1
                else:
                    assert current=='R' and ((dx==0) != (dy==0))
                assert e[5]==([[d,'capture_to_hand']] if destination==d else [])
            assert step['node']==dict(base=row['base'],current=e[6],square=destination)
            assert step['completed']==(destination==d)
            source=destination;current=e[6]
        assert row['complete'] and row['steps'][-1]['completed']


def test_optional_promotion_and_board_held_exclusions_remain_explicit():
    r=report()
    for row in r['routes']:
        if row['base']!='B':
            continue
        table=next(t for t in r['board_tables'] if t['owner']==row['owner']
                   and t['node']==dict(base='B',current='B',square=row['drop']))
        forms={x['key'][6] for x in table['events'] if x['key'][3]==row['quiet']
               and x['key'][4]=='empty'}
        assert forms=={'B','TB'}
        assert table['excluded_held']==['legacy_B_drop']
        assert table['excluded_dynamic'] and not table['excluded_history']
        assert not table['excluded_auxiliary_effects']
