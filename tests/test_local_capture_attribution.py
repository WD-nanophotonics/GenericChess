import hashlib
import json
from pathlib import Path

import pytest

from generic_chess.core.actions import action_from_dict, action_to_dict
from generic_chess.core.semantic_executor import iter_semantic_public_actions, semantic_engine_for
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_local_capture_attribution import audit, local_success, state_hash
from scripts.audit_secured_exchange_common_context import Budget
from scripts.label_joint_capability_corpus import INPUT, load_root

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def result():
    return audit()


def test_complete_frozen_reproduction_and_target_separation(result):
    recorded = json.loads((ROOT / 'docs/research/data/local_capture_attribution_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['materialized_transitions'] == 4971
    for game, captures, secured in (('chess', 63, 20), ('shogi', 55, 31)):
        row = result['games'][game]
        assert row['capture_actions'] == captures and row['secured_local_actions'] == secured
        assert row['global_success_actions'] == 0
        assert len(row['roots']) == 4
        assert all(len(reply['state_sha256']) == 64 for root in row['roots'] for action in root['actions'] for reply in action['replies'])


def test_public_reply_oracle_for_success_and_refutation_each_game(result):
    corpus = json.loads(INPUT.read_text())
    for game, compiled in (('chess', standard_engine()[0]),
                           ('shogi', compile_ruleset_for_execution(build_standard_shogi_ruleset()))):
        for wanted in (True, False):
            index, record = next((i, a) for i, root in enumerate(result['games'][game]['roots'])
                                 for a in root['actions'] if a['local_success'] == wanted and a['replies'])
            state = load_root(compiled, game, corpus['games'][game]['reference'][index])
            action = action_from_dict(record['action'])
            child = apply_action(state, action, compiled)
            assert state_hash(child, compiled) == record['capture_state_sha256']
            target = action.to_square.rank * compiled.board_size + action.to_square.file
            actor = child.position.board[target]
            public = {json.dumps(action_to_dict(a), sort_keys=True): a for a in
                      iter_semantic_public_actions(semantic_engine_for(compiled), child.position)}
            assert len(public) == len(record['replies'])
            assert set(public) == {json.dumps(r['action'], sort_keys=True) for r in record['replies']}
            local = []
            for reply in record['replies']:
                after = apply_action(child, public[json.dumps(reply['action'], sort_keys=True)], compiled)
                assert state_hash(after, compiled) == reply['state_sha256']
                owned = after.position.board[target] == actor
                assert owned == reply['actor_owned']
                assert after.position.hands[0] == child.position.hands[0]
                terminal_ok = not after.terminal_status.is_terminal or after.terminal_status.winner == 0
                local.append(owned and terminal_ok)
            assert all(local) == wanted


def test_terminal_contract_does_not_ignore_physical_loss():
    assert local_success(True, True, 'ongoing', None)
    assert local_success(True, True, 'win', 0)
    assert not local_success(False, True, 'win', 0)
    assert not local_success(True, False, 'win', 0)
    assert not local_success(True, True, 'draw', None)
    assert not local_success(True, True, 'win', 1)
    with pytest.raises(ValueError):
        local_success(True, True, 'no_contest', None)


def test_abort_does_not_qualify_partial_actions():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(seconds=15, transitions_limit=1))
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
