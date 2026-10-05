"""Actual alternating reply destroys the tagged-source task, not a WDL claim."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shogi_active_rook_20261005.json'


def test_complete_public_membership_real_alternation_and_history():
    r=json.loads(RAW.read_text());assert r['complete'] and r['public_transitions']==2
    assert r['enumerated']==139 and r['goal_queries']==0 and r['seconds']<15
    for i,row in enumerate(r['steps']):
        assert row['action'] in row['all_actions'] and len(row['all_actions'])<=128
        assert row['mover_safe'] and row['ledger']==r['initial_ledger']
        assert row['before']['position']['side_to_move']==i
        assert row['after']['position']['side_to_move']==1-i
        assert row['after']['ply_count']==i+1 and len(row['after']['history'])==i+2
    assert r['steps'][1]['before']==r['steps'][0]['after']


def test_source_origin_custody_destroyed_despite_safe_first_drop():
    r=json.loads(RAW.read_text());drop,reply=r['steps']
    p=drop['after']['position']['board'][13]
    assert p['base_type_id']==p['current_type_id']=='P' and p['owner']==0
    assert reply['after']['position']['board'][13]['base_type_id']=='R'
    assert reply['after']['position']['board'][76] is None
    assert reply['after']['position']['hands'][1]['counts']==[['P',17]]
    assert r['source_removed'] and r['owner_checked_again']


def test_active_counterstrategy_frozen_inputs_match():
    r=json.loads(RAW.read_text());assert r['source_hashes_unchanged']
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
