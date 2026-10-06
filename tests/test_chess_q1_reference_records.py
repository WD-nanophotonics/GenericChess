import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def load(name):return json.loads((ROOT/f'docs/research/data/chess_q1_reference_{name}_20261006.json').read_text())


def test_prospective_local_admission_and_all_original_pins():
    r=load('local');assert r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['preflight']==dict(root_actions=5,all_replies=22,combined_event_upper_bound=93,source_trees_qualified=True,external_labels_read=False)
    assert r['public_transitions']==r['source_pushes']==27
    assert r['runtime_pushes']==r['runtime_pops']==66
    assert r['source_entries']==76 and r['entries']==426 and r['qnodes']==21
    for law,row in r['policies'].items():
        assert row['scores']==row['reference']
        assert row['full_ties']==['a1a2','a1b1','a1b2']
        assert row['scores']['c2c3']==row['scores']['c2c4']==-row['integer_weights']['P']
        assert set(row['static_scores'].values())=={0}


def test_actual_single_transport_failure_is_not_an_outcome_certificate():
    r=load('external');assert not r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['request_attempts']==1 and '10013' in r['error']
    assert 'http_status' not in r and 'root_owner_outcomes' not in r
    assert r['local_policy_record_sha256']==hashlib.sha256((ROOT/'docs/research/data/chess_q1_reference_local_20261006.json').read_bytes()).hexdigest()
    assert not (ROOT/'docs/research/data/chess_q1_reference_external_20261006.response.json').exists()
