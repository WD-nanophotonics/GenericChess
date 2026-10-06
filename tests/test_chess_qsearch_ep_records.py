import hashlib
import json
from pathlib import Path
from scripts.chess_complete_child_noisy import opponent_removal
from scripts.research_state_replay import read_game_state

ROOT=Path(__file__).resolve().parents[1]


def record():
    return json.loads((ROOT/'docs/research/data/chess_qsearch_ep_20261006.json').read_text())


def test_frozen_complete_check_and_strict_budget():
    r=record()
    assert r['complete'] and r['source_hashes_unchanged'] and r['seconds']<15
    for p,pin in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    assert r['public_transitions']==r['source_pushes']==35
    assert r['runtime_pushes']==r['runtime_pops']==30
    assert r['entries']==269 and r['source_entries']==119
    assert len(r['children'])==31 and r['compilations']==1


def test_actual_nonchecking_nonterminal_ep_omission_is_preserved():
    r=record(); root=read_game_state(r['root']); row=r['children']['e5d6']
    child=read_game_state(row['state'])
    assert row['is_ep'] and row['is_capture'] and row['opponent_removed']
    assert not row['gives_check'] and not child.terminal_status.is_terminal
    assert root.position.board[43] is None and root.position.board[35] is not None
    assert child.position.board[35] is None and child.position.board[43].owner==0
    assert not row['immutable_noisy'] and not row['runtime_noisy'] and row['adapter_noisy']


def test_full_history_and_all_child_removals_match_source():
    r=record(); root=read_game_state(r['root'])
    assert root.ply_count==4 and len(root.history)==5
    assert [row['uci'] for row in r['prefix']]==['e2e4','a7a6','e4e5','d7d5']
    for row in r['children'].values():
        child=read_game_state(row['state'])
        assert child.ply_count==5 and len(child.history)==6
        assert not child.terminal_status.is_terminal
        assert opponent_removal(root,child)==row['is_capture']==row['opponent_removed']


def test_control_noisy_actions_not_erased_and_capture_counter_corrected():
    r=record()
    assert set(r['immutable_noisy'])==set(r['runtime_noisy'])=={'f1b5','f1a6'}
    assert set(r['adapter_noisy'])=={'f1b5','f1a6','e5d6'}
    assert r['immutable_captures']==r['runtime_captures']==1
    assert r['adapter_captures']==2
