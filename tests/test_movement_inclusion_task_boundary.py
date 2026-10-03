import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_movement_inclusion_task_boundary import audit, coordinates
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def result():
    return audit()


def test_coordinate_superset_can_reverse_task_root_order_through_stalemate(result):
    rook, queen = result['roots']
    assert result['complete'] and result['rook_coordinate_actions_included_in_queen']
    assert coordinates(rook['root']) < coordinates(queen['root'])
    assert rook['root']['success'] == 1 and queen['root']['success'] == 0
    assert rook['selected_capture']['action']['to'] == queen['selected_capture']['action']['to'] == [3, 4]
    assert rook['immediate_custody_gain'] == queen['immediate_custody_gain'] == 1
    assert not rook['opponent_in_check'] and not queen['opponent_in_check']
    assert rook['capture_terminal'] == 'ongoing' and queen['capture_terminal'] == 'stalemate'
    assert rook['raw_position_replies'][0]['to'] == [6, 7]
    assert len(rook['raw_position_replies']) == 1 and queen['raw_position_replies'] == []
    assert rook['selected_capture']['success'] and not queen['selected_capture']['success']


def test_complete_evidence_is_frozen_and_counts_replays(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/movement_inclusion_task_boundary_20261003.json').read_text())
    assert result['materialized_transitions'] == 94 and result['replayed_transitions'] == 2
    assert result['materialized_transitions'] == result['replayed_transitions'] + sum(
        1 + action['reply_count'] for row in result['roots'] for action in row['root']['actions'])
    assert result['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_movement_inclusion_task_boundary.py').read_bytes()).hexdigest()
    for key in ('protocol_sha256', 'program_sha256', 'physical_board', 'roots', 'materialized_transitions'):
        assert result[key] == recorded[key]


def test_abort_is_not_a_type_ranking():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(transitions_limit=1))
