"""Complete saved guarded route; no frozen producer rerun."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shogi_royal_source_route_20261005.json'


def test_saved_complete_route_real_membership_safety_and_turn_scope():
    r=json.loads(RAW.read_text());assert r['complete'] and r['initial_checked']
    assert r['virtual_materializations']==len(r['steps'])==8
    assert r['enumerated_actions']==124 and r['seconds']<15
    assert r['public_transitions']==r['goal_queries']==0
    for i,row in enumerate(r['steps']):
        assert row['action'] in row['all_actions'] and row['owner_safe_after']
        assert row['raw_after']['side_to_move']==1
        assert row['next_virtual_position']['side_to_move']==(0 if i<7 else 1)
        assert row['ledger']==r['initial_ledger']
        if i:
            assert row['before']==r['steps'][i-1]['next_virtual_position']
            assert row['raw_after']['board'][row['action']['source']] is None
        source=row['raw_after']['board'][row['action']['target']]
        assert source['base_type_id']=='P' and source['owner']==0
        assert source['current_type_id']==('P' if i<5 else 'TP')
        assert source['promoted']==(i>=5)


def test_drop_custody_and_capture_base_transfer_are_not_score_refresh():
    r=json.loads(RAW.read_text());first=r['steps'][0];last=r['steps'][-1]
    assert first['before']['hands'][0]['counts']==[['P',1]]
    assert first['raw_after']['hands'][0]['counts']==[]
    assert last['before']['board'][76]['current_type_id']=='R'
    assert last['raw_after']['hands'][0]['counts']==[['R',1]]
    assert last['raw_after']['board'][76]['base_type_id']=='P'
    assert last['raw_after']['board'][4]==first['before']['board'][4]  # fixed own King
    assert last['raw_after']['board'][80]==first['before']['board'][80]  # passive enemy King


def test_frozen_route_inputs_match():
    r=json.loads(RAW.read_text());assert r['source_hashes_unchanged']
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
