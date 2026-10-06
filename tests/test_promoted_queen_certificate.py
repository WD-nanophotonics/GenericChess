from copy import deepcopy
from pathlib import Path
import hashlib,json,pytest
from scripts.verify_promoted_queen_certificate import verify
ROOT=Path(__file__).resolve().parents[1]
RAW='docs/research/data/promoted_queen_strategy_20261006.json'

@pytest.fixture(scope='module')
def certificate():return json.loads((ROOT/RAW).read_text())

def test_source_free_all_path_replay(certificate):
    r=verify(certificate)
    assert r['complete'] and r['owner_zero_win'] and r['full_path_history_replay']
    assert r['source_calls']==0 and r['mate_leaves']>0 and r['max_absolute_ply']<=15

def test_missing_defense_rejected(certificate):
    r=deepcopy(certificate);root=r['nodes'][r['root']]
    root['strategy'].pop(next(iter(root['strategy'])))
    with pytest.raises(ValueError,match='missing defender'):verify(r)

def test_nondecreasing_edge_rejected(certificate):
    r=deepcopy(certificate);root=r['nodes'][r['root']]
    root['strategy'][next(iter(root['strategy']))]=r['root']
    with pytest.raises(ValueError,match='strictly decreasing'):verify(r)

def test_false_winner_rejected(certificate):
    r=deepcopy(certificate)
    for n in r['nodes'].values():
        if n['terminal']=='checkmate':n['winner']=1
    with pytest.raises(ValueError,match='White mate'):verify(r)

def test_certificate_and_verifier_pins(certificate):
    for r in (certificate,json.loads((ROOT/'docs/research/data/promoted_queen_verification_20261006.json').read_text())):
        assert r['complete']
        for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
