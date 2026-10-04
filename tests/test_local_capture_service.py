from dataclasses import replace
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.position import Hands
from generic_chess.core.semantic_executor import iter_semantic_public_actions, semantic_engine_for
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_secured_exchange_common_context import Budget
from scripts.label_joint_capability_corpus import INPUT, load_root
from scripts.local_capture_service import service_labels

ROOT = Path(__file__).resolve().parents[1]


def test_helper_equals_complete_exposed_capture_diagnostic():
    corpus = json.loads(INPUT.read_text())
    diagnostic = json.loads((ROOT / 'docs/research/data/local_capture_attribution_20261004.json').read_text())
    for game, compiled in (('chess', standard_engine()[0]),
                           ('shogi', compile_ruleset_for_execution(build_standard_shogi_ruleset()))):
        state = load_root(compiled, game, corpus['games'][game]['reference'][0])
        labels = service_labels(compiled, state, Budget(seconds=10, transitions_limit=10000))
        actual = {json.dumps(a['action'], sort_keys=True): (a['success'], a['reply_count'])
                  for actor in labels['actors'] for a in actor['actions']}
        expected = {json.dumps(a['action'], sort_keys=True): (a['local_success'], len(a['replies']))
                    for a in diagnostic['games'][game]['roots'][0]['actions']}
        assert actual == expected
        assert labels['actor_success_count'] == sum(actor['success'] for actor in labels['actors'])


def test_held_opponent_reply_scope_with_public_action_oracle():
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    fixture = json.loads((ROOT / 'docs/research/data/post_capture_scope_20261004.json').read_text())['roots'][1]
    parent = load_root(compiled, 'shogi', fixture['parent'])
    state = apply_action(parent, action_from_dict(fixture['selected_capture']['action']), compiled)
    assert state.position.hands[1].total() > 0
    labels = service_labels(compiled, state, Budget(seconds=10, transitions_limit=10000))
    assert labels['opponent_drop_replies'] == 50
    assert sum(len(actor['actions']) for actor in labels['actors']) == 14
    for actor in labels['actors']:
        for row in actor['actions']:
            child = apply_action(state, action_from_dict(row['action']), compiled)
            replies = list(iter_semantic_public_actions(semantic_engine_for(compiled), child.position))
            assert row['reply_count'] == len(replies)
            assert row['opponent_drop_replies'] == sum(getattr(r, 'from_square', None) is None for r in replies)
            assert all(apply_action(child, r, compiled).position.hands[0] == child.position.hands[0] for r in replies)


def test_empty_own_hand_and_complete_budget_required():
    compiled = standard_engine()[0]
    corpus = json.loads(INPUT.read_text())
    state = load_root(compiled, 'chess', corpus['games']['chess']['reference'][0])
    held = replace(state, position=replace(state.position, hands=(Hands.empty().add('P'), Hands.empty())))
    with pytest.raises(ValueError, match='empty own hand'):
        service_labels(compiled, held, Budget(seconds=10))
    with pytest.raises(RuntimeError, match='transition cap'):
        service_labels(compiled, state, Budget(seconds=10, transitions_limit=1))
    with pytest.raises(TimeoutError):
        service_labels(compiled, state, Budget(seconds=-1))
