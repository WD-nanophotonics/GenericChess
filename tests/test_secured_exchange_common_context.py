from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from scripts.audit_exchange_custody import synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_secured_exchange_common_context import Budget, audit, context_position, root_score


@pytest.fixture(scope='module')
def result():
    return audit()


def test_frozen_geometry_and_resistance_predictions(result):
    assert result['complete'] and len(result['roots']) == 15
    assert result['scores'] == {'chess': {'B': '1/3', 'R': '1/3', 'Q': '2/3'},
                                'shogi': {'B': '1/3', 'R': '1/3'}}
    assert all(row['success'] == 0 for row in result['roots'] if row['context'] == 'diagonal_defended')
    # Complete enumeration, including refuted/irrelevant actions, not success pruning.
    assert result['materialized_transitions'] == sum(1 + action['reply_count']
        for row in result['roots'] for action in row['actions'])
    assert result['materialized_transitions'] <= 20_000


def test_published_evidence_reproduces_without_silent_source_rebase(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/secured_exchange_common_context_20261003.json').read_text())
    assert recorded['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_secured_exchange_common_context.py').read_bytes()).hexdigest()
    for field in ('protocol_sha256', 'program_sha256', 'complete', 'scores', 'roots', 'materialized_transitions'):
        assert recorded[field] == result[field]


def test_full_public_focal_action_set_is_preserved(result):
    compiled, _ = standard_engine()
    position = context_position(compiled, 'chess', 'Q', 'diagonal_open')
    state = synthetic_state(compiled, position)
    expected = [action_to_dict(a) for a in legal_actions(state, compiled)
                if getattr(a, 'from_square', None) and (a.from_square.file, a.from_square.rank) == (3, 3)]
    row = next(r for r in result['roots'] if r['game'] == 'chess' and r['focal_type'] == 'Q'
               and r['context'] == 'diagonal_open')
    assert [a['action'] for a in row['actions']] == expected


def test_invalid_common_context_is_not_dropped_or_scored_zero():
    compiled, _ = standard_engine()
    position = context_position(compiled, 'chess', 'B', 'orthogonal_open')
    board = list(position.board); board[6 * 8 + 7] = None
    board[7 * 8 + 7] = Piece(1, 'K', 'K')  # nonmoving king is illegally in check
    with pytest.raises(ValueError, match='invalid common context'):
        root_score(compiled, replace(position, board=tuple(board)), Budget())


def test_transition_cap_aborts_without_complete_vector():
    with pytest.raises(RuntimeError, match='no complete vector'):
        audit(Budget(transitions_limit=1))


def test_time_cap_aborts_without_complete_vector():
    with pytest.raises(TimeoutError, match='no complete vector'):
        audit(Budget(seconds=-1))
