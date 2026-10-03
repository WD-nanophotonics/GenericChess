from dataclasses import replace
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for, iter_semantic_public_actions
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_exchange_custody import custody, synthetic_state
from scripts.audit_f24f_western_chess_perft import standard_engine, position_from_fen
from scripts.audit_post_capture_scope import audit, board_actor_labels, capture_key, state_evidence
from scripts.audit_secured_exchange_common_context import Budget, task_success


@pytest.fixture(scope='module')
def result():
    return audit()


def public_states(row):
    compiled = standard_engine()[0] if row['game'] == 'chess' else compile_ruleset_for_execution(build_standard_shogi_ruleset())
    template = position_from_fen('8/8/8/8/8/8/8/8 b - - 0 1', compiled) if row['game'] == 'chess' else initial_state(compiled).position
    position = replace(template, board=tuple(None if p is None else Piece(*p) for p in row['parent']['physical_board']), side_to_move=1)
    parent = synthetic_state(compiled, position)
    child = apply_action(parent, action_from_dict(row['selected_capture']['action']), compiled)
    return compiled, parent, child


def test_real_capture_preserves_full_child_state_and_changes_inventory(result):
    for row, actor_count in zip(result['roots'], (14, 18)):
        compiled, parent, child = public_states(row)
        assert state_evidence(parent, compiled) == row['parent']
        assert state_evidence(child, compiled) == row['child']
        assert child.ply_count == 1 and child.history[-1].actor == 1
        assert child.position.side_to_move == 0 and child.position.hands[0].total() == 0
        assert len(row['actors']) == actor_count
        if row['game'] == 'chess':
            assert semantic_engine_for(compiled).in_check(child.position, 0)
            assert row['selected_capture']['victim_type'] == 'B'
        else:
            assert child.position.hands[1].count('P') == 1
            assert row['opponent_drop_replies'] == 50


def test_capture_coverage_and_actor_evasions_match_public_actions(result):
    for row in result['roots']:
        compiled, parent, child = public_states(row)
        engine = semantic_engine_for(compiled)
        actions = list(iter_semantic_public_actions(engine, parent.position))
        assert len(actions) == row['legal_parent_actions']
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        captures = []
        for action in actions:
            target = getattr(action, 'to_square', None)
            victim = None if target is None else parent.position.board[target.rank * compiled.board_size + target.file]
            if victim and victim.owner == 0 and victim.current_type_id not in anchors:
                captures.append(capture_key(action_to_dict(action)))
        assert len(set(captures)) == len(captures)
        assert sorted(captures) == sorted(r['key'] for r in row['captures'])
        sources = {tuple(r['source']) for r in row['actors']}
        public = [capture_key(action_to_dict(a)) for a in iter_semantic_public_actions(engine, child.position)
                  if getattr(a, 'from_square', None) is not None and (a.from_square.file, a.from_square.rank) in sources]
        assert sorted(public) == sorted(capture_key(a['action']) for actor in row['actors'] for a in actor['actions'])


def test_full_reply_counts_include_hand_drops_and_refutations(result):
    for row in result['roots']:
        compiled, _, child = public_states(row)
        anchors = {tid for tid, item in compiled.support.type_metadata.items() if item.is_anchor}
        baseline = custody(child.position, anchors)
        for actor in row['actors']:
            for item in actor['actions']:
                after = apply_action(child, action_from_dict(item['action']), compiled)
                if after.terminal_status.is_terminal:
                    assert item['reply_count'] == 0 and item['success'] == task_success(after, anchors, baseline)
                    continue
                replies = list(iter_semantic_public_actions(semantic_engine_for(compiled), after.position))
                assert len(replies) == item['reply_count'] > 0
                assert sum(getattr(a, 'from_square', None) is None for a in replies) == item['opponent_drop_replies']
                if item['first_refutation']:
                    state = apply_action(after, action_from_dict(item['first_refutation']['action']), compiled)
                    assert not task_success(state, anchors, baseline)
                if item['success']:
                    assert all(task_success(apply_action(after, a, compiled), anchors, baseline) for a in replies)


def test_frozen_evidence_and_materialization_accounting(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/post_capture_scope_20261004.json').read_text())
    for key in ('protocol_sha256', 'input_sha256', 'program_sha256', 'complete', 'scope', 'roots', 'materialized_transitions'):
        assert recorded[key] == result[key]
    assert result['materialized_transitions'] == 1988
    assert result['materialized_transitions'] == sum(len(r['captures']) + sum(1 + a['reply_count']
                for actor in r['actors'] for a in actor['actions']) for r in result['roots'])


def test_aborted_or_unsupported_deployment_does_not_return_labels(result):
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(seconds=15, transitions_limit=1))
    compiled, parent, child = public_states(result['roots'][0])
    with pytest.raises(ValueError, match='owner-zero'):
        board_actor_labels(compiled, parent, Budget())
    own_hand = child.position.hands[0].add('P')
    unsupported = replace(child, position=replace(child.position, hands=(own_hand, child.position.hands[1])))
    with pytest.raises(ValueError, match='own hand actors'):
        board_actor_labels(compiled, unsupported, Budget())
