import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_complete_stock_checked_drop_witness_and_all_actions():
    r=json.loads((ROOT/'docs/research/data/shogi_checked_drop_guard_20261005.json').read_text())
    assert r['complete'] and r['owner_checked'] and r['previous_owner_safe'] and r['ongoing']
    assert r['resource_ledger']['inventory']=={'K':2,'P':18,'L':4,'N':4,'S':4,'G':4,'B':2,'R':2}
    assert len(r['masked_drops'])==63 and r['legal_drops']==[9*i+4 for i in range(1,8)]
    assert len(r['removed'])==56 and r['enumerated']==len(r['all_action_ids'])==11
    assert len([a for a in r['all_action_ids'] if 'P@' not in a])==4
    assert set(r['masked_drops'])==set(r['removed'])|set(r['legal_drops'])
    assert r['public_transitions']==r['goal_queries']==0 and r['seconds']<15


def test_witness_retains_full_history_opponent_hand_and_pins():
    r=json.loads((ROOT/'docs/research/data/shogi_checked_drop_guard_20261005.json').read_text())
    s=r['root_state'];assert s['ply_count']==0 and len(s['history'])==1
    assert s['position']['hands'][1]  # full opponent stock not omitted
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
