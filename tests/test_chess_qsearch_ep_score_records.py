import hashlib,json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from scripts.chess_capture_effect_hint import ChessCaptureEffectHint
from scripts.native_chess_contact_intervals import FINGERPRINT
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1]


def test_actual_qsearch_capture_and_full_restoration_records():
    r=json.loads((ROOT/'docs/research/data/chess_qsearch_ep_score_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged'] and r['seconds']<15
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['public_transitions']==r['source_pushes']==6
    assert r['runtime_pushes']==r['runtime_pops']==11
    assert r['entries']==88 and r['source_entries']==10
    assert len(r['children'])==5 and r['reference_noisy']==['e5d6']
    root=read_game_state(r['root']);assert root.ply_count==1 and len(root.history)==2
    for row in r['children'].values():
        c=read_game_state(row['state']);assert c.ply_count==2 and len(c.history)==3
    old,new=r['runs'];assert old['score']==0
    assert new['score']==r['reference_score']==r['integer_weights']['P']==17417
    assert old['runtime_pushes']==5 and new['runtime_pushes']==6
    assert old['stats']['qnodes']==1 and new['stats']['qnodes']==2
    assert new['stats']['capture_qactions']==1 and new['stats']['qdepth_cutoffs']==1
    for run in r['runs']:
        assert not run['stats']['qsearch_budget_aborts'] and not run['stats']['qsearch_check_hard_limit_aborts']


def test_first_cheap_hint_failure_preserved_without_tree_retries():
    r=json.loads((ROOT/'docs/research/data/chess_capture_effect_hint_20261006.json').read_text())
    assert not r['complete'] and r['error']=='ValueError: unqualified effect vocabulary'
    assert r['source_hashes_unchanged'] and r['compilations']==1 and r['terms']==0
    assert r['public_transitions']==r['runtime_pushes']==r['source_pushes']==0
    for p,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin


def test_hint_rejects_native_clear_right_instead_of_silent_fallback():
    p=NS(pattern_id='legal_id',effects=[NS(kind='clear_right')])
    with pytest.raises(ValueError,match='vocabulary'):ChessCaptureEffectHint(FINGERPRINT,[p])


def test_hint_checked_ownership_not_debug_names_or_destination():
    remove=NS(kind='remove',piece_owner='opponent',disposition='remove_from_game')
    p=NS(pattern_id='quiet_debug',effects=[remove]);h=ChessCaptureEffectHint(FINGERPRINT,[p])
    assert h.legal_pattern_captures('quiet_debug')
    with pytest.raises(ValueError,match='unknown'):h.legal_pattern_captures('unbound')
    for owner in ('self','any'):
        p=NS(pattern_id='capture_debug',effects=[NS(kind='remove',piece_owner=owner,disposition='remove_from_game')])
        with pytest.raises(ValueError,match='ownership'):ChessCaptureEffectHint(FINGERPRINT,[p])
