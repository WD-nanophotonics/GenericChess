from frozen_research_sources import source_digest
import hashlib,json
from pathlib import Path
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1]


def record():return json.loads((ROOT/'docs/research/data/chess_q1_root_20261006.json').read_text())


def test_complete_scoped_root_and_all_original_pins():
    r=record();assert r['complete'] and r['source_hashes_unchanged']
    for p,pin in r['source_sha256'].items():assert source_digest(ROOT, p, pin) == pin
    assert r['public_transitions']==r['source_pushes']==22
    assert r['runtime_pushes']==r['runtime_pops']==54
    assert r['entries']==356 and r['qnodes']==18 and r['seconds']<15
    assert len(r['children'])==4 and sum(len(x['replies']) for x in r['children'].values())==18


def test_capture_sensitive_scores_full_ties_and_unchanged_models():
    r=record()
    for law,row in r['policies'].items():
        assert row['scores']==row['reference']
        assert row['full_ties']==['a1a2','a1b1'] and row['canonical']=='a1a2'
        assert row['static_scores']==dict.fromkeys(row['scores'],0)
        assert row['scores']['b2b3']==row['scores']['b2b4']==-row['integer_weights']['P']
        assert row['runtime_pushes']==18 and row['entries']==104 and row['qnodes']==6
        assert sum(s['capture_qactions'] for s in row['statistics'].values())==2


def test_complete_true_synthetic_history_including_ep_child():
    r=record();root=read_game_state(r['root']);assert root.ply_count==0 and len(root.history)==1
    for row in r['children'].values():
        s=read_game_state(row['state']);assert s.ply_count==1 and len(s.history)==2
        for reply in row['replies'].values():
            c=read_game_state(reply['state']);assert c.ply_count==2 and len(c.history)==3
            assert not c.terminal_status.is_terminal
    assert r['children']['b2b4']['replies']['c4b3']['ep']
    assert r['children']['b2b3']['replies']['c4b3']['capture']
    assert not r['children']['b2b3']['replies']['c4b3']['ep']


def test_source_annotation_counter_limitation_has_bounded_correction():
    r=record();counts=[len(x['replies']) for x in r['children'].values()]
    assert sorted(counts)==[4,4,5,5]
    assert r['source_entries']==22
    assert 2*sum(n*n for n in counts)==164
    assert r['source_entries']+164==186<5000
