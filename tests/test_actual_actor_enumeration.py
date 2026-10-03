from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_actor_enumeration import audit, all_actor_labels, inventory
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_secured_exchange_common_context import Budget, task_success


@pytest.fixture(scope='module')
def result():
    return audit()


def fixture_state(game, row):
    compiled = standard_engine()[0] if game == 'chess' else compile_ruleset_for_execution(build_standard_shogi_ruleset())
    template = position_from_fen('8/8/8/8/8/8/8/8 w - - 0 1', compiled) if game == 'chess' else initial_state(compiled).position
    position = replace(template, board=tuple(None if p is None else Piece(*p) for p in row['physical_board']))
    return compiled, synthetic_state(compiled, position)


def test_unchanged_actual_inventory_and_complete_source_groups(result):
    for row, expected_count in zip(result['roots'], (15, 19)):
        compiled, state = fixture_state(row['game'], row)
        assert inventory(state.position) == inventory(initial_state(compiled).position)
        assert len(row['actors']) == expected_count
        sources = {tuple(actor['source']) for actor in row['actors']}
        public = [action_to_dict(a) for a in iter_semantic_public_actions(semantic_engine_for(compiled), state.position)
                  if hasattr(a, 'from_square') and (a.from_square.file, a.from_square.rank) in sources]
        grouped = [item['action'] for actor in row['actors'] for item in actor['actions']]
        key = lambda a: json.dumps(a, sort_keys=True)
        assert sorted(map(key, public)) == sorted(map(key, grouped))
        assert sum(len(actor['actions']) for actor in row['actors']) == len(public)
        assert sum(Fraction(t['marked_actor_mean']) * t['count'] for t in row['types'].values()) == row['actor_success_count']


def test_successes_and_recorded_refutations_replay_public_transitions(result):
    for row in result['roots']:
        compiled, state = fixture_state(row['game'], row)
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        baseline = custody(state.position, anchors)
        for actor in row['actors']:
            for item in actor['actions']:
                if item['success'] or item['first_refutation'] is not None:
                    child = apply_action(state, action_from_dict(item['action']), compiled)
                    if item['success']:
                        if child.terminal_status.is_terminal:
                            assert task_success(child, anchors, baseline)
                        else:
                            replies = list(iter_semantic_public_actions(semantic_engine_for(compiled), child.position))
                            assert len(replies) == item['reply_count'] > 0
                            assert all(task_success(apply_action(child, reply, compiled), anchors, baseline) for reply in replies)
                    else:
                        refutation = item['first_refutation']
                        after = apply_action(child, action_from_dict(refutation['action']), compiled)
                        assert not task_success(after, anchors, baseline)
                        assert custody(after.position, anchors) - baseline == refutation['custody_delta']


def test_complete_evidence_reproduces_and_cost_is_accounted(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/actual_actor_enumeration_20261004.json').read_text())
    for key in ('protocol_sha256', 'input_sha256', 'program_sha256', 'complete', 'roots', 'materialized_transitions'):
        assert recorded[key] == result[key]
    assert result['complete'] and result['materialized_transitions'] == 2107
    assert result['materialized_transitions'] == sum(1 + item['reply_count'] for row in result['roots']
                                                   for actor in row['actors'] for item in actor['actions'])


def test_aborts_and_inventory_substitution_do_not_yield_complete_labels(result):
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(transitions_limit=1))
    compiled, state = fixture_state('chess', result['roots'][0])
    board = list(state.position.board)
    source = next(i for i, p in enumerate(board) if p and p.owner == 0 and p.current_type_id == 'P')
    board[source] = Piece(0, 'Q', 'Q')
    with pytest.raises(ValueError, match='actual initial board inventory'):
        all_actor_labels(compiled, replace(state.position, board=tuple(board)), Budget())
