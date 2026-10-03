from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_constructed_physical_support import audit, physical_frame
from scripts.audit_constructed_shogi_support import audit as shogi_audit, physical_frame as shogi_frame
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_secured_exchange_common_context import Budget


def test_full_inventory_witness_is_legal_mate_in_common_physical_support():
    result = audit()
    assert result['complete'] and result['initial_inventory_preserved'] and result['common_screen_passed']
    assert result['root']['success'] == 1 and result['selected_capture']['success']
    assert result['terminal'] == 'checkmate' and result['winner'] == 0
    assert result['opponent_in_check'] and result['raw_position_legal_reply_count'] == 0
    assert result['materialized_transitions'] == 130
    assert result['materialized_transitions'] == 1 + sum(1 + row['reply_count'] for row in result['root']['actions'])
    compiled, _ = standard_engine()
    count = lambda pos: Counter((p.owner, p.base_type_id) for p in pos.board if p)
    assert count(physical_frame(compiled)) == count(initial_state(compiled).position)
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/constructed_physical_support_20261003.json').read_text())
    assert result['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_constructed_physical_support.py').read_bytes()).hexdigest()
    for key in ('protocol_sha256', 'program_sha256', 'physical_board', 'root', 'selected_capture', 'terminal', 'winner'):
        assert result[key] == recorded[key]


def test_materialization_limit_does_not_emit_complete_witness():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(transitions_limit=1))


def test_shogi_full_inventory_board_mate_preserves_common_files_and_custody():
    result = shogi_audit()
    assert result['complete'] and result['common_screen_passed']
    assert result['root']['success'] == 1 and result['selected_capture']['success']
    assert result['terminal'] == 'checkmate' and result['winner'] == 0
    assert result['opponent_in_check'] and result['raw_position_legal_reply_count'] == 0
    assert result['selected_capture']['action']['kind'] == 'semantic_board'
    assert result['hand_pawn_gain'] == 1 and result['custody_gain'] == 2
    assert result['materialized_transitions'] == 314
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    frame = shogi_frame(compiled)
    count = lambda pos: Counter((p.owner, p.base_type_id) for p in pos.board if p)
    assert count(frame) == count(initial_state(compiled).position)
    for owner in (0, 1):
        files = [cell % 9 for cell, p in enumerate(frame.board) if p and p.owner == owner and p.current_type_id == 'P']
        assert sorted(files) == list(range(9))
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/constructed_shogi_support_20261003.json').read_text())
    assert result['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_constructed_shogi_support.py').read_bytes()).hexdigest()
    for key in ('protocol_sha256', 'program_sha256', 'physical_board', 'root', 'selected_capture', 'terminal', 'winner'):
        assert result[key] == recorded[key]


def test_shogi_materialization_limit_is_not_a_zero_support_claim():
    with pytest.raises(RuntimeError, match='transition cap'):
        shogi_audit(Budget(transitions_limit=1))
