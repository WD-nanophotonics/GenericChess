"""Frozen prelabel history and source/tie evidence, no new tablebase calls."""
from collections import Counter
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/data'


def read(name):return json.loads((DATA/name).read_text())


def test_capture_only_full_history_and_source_opportunity_before_labels():
    pre=read('chess_double_check_20261005.selections.json')
    assert pre['complete'] and pre['source_queries']==0
    assert pre['public_transitions']==4 and pre['enumerated']==56
    for row in pre['rows']:
        assert row['weight']=='1/2' and len(row['all_root_actions'])==2
        assert set(row['all_root_actions'])==set(row['children'])
        assert {v['signature'] for v in row['children'].values()}=={'BKK','KKR'}
        for child in row['children'].values():
            q=child['request'];s=q['local_state']
            assert q['absolute_ply']==1 and q['remaining_horizon']==999
            assert len(s['history'])==2 and s['terminal_status']['status']=='ongoing'
            assert dict(s['repetition_counts'])==Counter(h['position_key'] for h in s['history'])
            assert q['source_verified'] is False
        for name in ('unit','zero'):
            assert set(row['selections_before_labels'][name]['tie_set'])==set(row['children'])


def test_conditional_source_answers_and_owner_relative_tie_margins():
    pre=read('chess_double_check_20261005.selections.json');out=read('chess_double_check_source_scope_20261005.json')
    assert out['complete'] and out['outer_probe_calls']==8 and out['cumulative_seconds']<15
    assert out['canonical_mean']=={'unit':0.5,'zero':0.5}
    assert out['tie_mean_interval']=={'unit':[0,1],'zero':[0,1]}
    for p,r in zip(pre['rows'],out['rows']):
        picks=p['selections_before_labels'];sign=1 if r['owner']==0 else -1
        values={k:c['interval'][0] for k,c in r['children'].items()}
        assert values[picks['contact_family']['selected']]==0
        assert set(sign*v for v in values.values())=={0,-1}
        for k,c in r['children'].items():
            assert c['request_sha256']==p['children'][k]['request']['state_sha256']
            assert c['projected_legal_count']==len(p['children'][k]['all_actions'])
            assert c['source_verified'] is False and c['bridge']['horizon']==999
            assert c['external_insufficient_material']==(p['children'][k]['signature']=='BKK')
        assert all(r['tie_margins'][n]==[0,1] for n in ('unit','zero'))


def test_failed_generic_terminal_guard_preserved_without_queries():
    failed=read('chess_double_check_source_20261005.json')
    assert not failed['complete'] and failed['outer_probe_calls']==0
    assert 'ongoing conversion premise' in failed['error']
    for name in ('chess_double_check_20261005.selections.json','chess_double_check_source_20261005.json','chess_double_check_source_scope_20261005.json'):
        r=read(name);assert r['source_hashes_unchanged']
        for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
