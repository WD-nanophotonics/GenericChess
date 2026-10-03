from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_nonterminal_physical_support import audit, control_frame
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def result():
    return audit()


def test_nonterminal_positive_support_does_not_use_mate_exception(result):
    assert result['complete'] and len(result['roots']) == 2
    for row in result['roots']:
        assert row['root']['success'] == 1 and row['selected_capture']['success']
        assert row['capture_terminal'] == 'ongoing' and row['opponent_in_check']
        assert row['selected_capture']['reply_count'] == len(row['replies']) == 1
        reply = row['replies'][0]
        assert reply['terminal'] == 'ongoing'
        assert reply['custody_delta'] == (1 if row['game'] == 'chess' else 2)
        assert reply['action']['actor_type_id'] == 'K'
        assert reply['action']['to'] == [1, 7 if row['game'] == 'chess' else 8]
    assert result['materialized_transitions'] == 465 and result['replayed_transitions'] == 4
    assert result['materialized_transitions'] == result['replayed_transitions'] + sum(
        1 + action['reply_count'] for row in result['roots'] for action in row['root']['actions'])


def test_only_nonpawn_permutation_and_frozen_sources_are_reproduced(result):
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    for game, compiled in [('chess', chess), ('shogi', shogi)]:
        before, after = control_frame(compiled, game)
        assert Counter(before.board) == Counter(after.board)
        changed = [index for index, pair in enumerate(zip(before.board, after.board)) if pair[0] != pair[1]]
        assert changed == [4, (6 if game == 'chess' else 7) * compiled.board_size + 2]
        assert all(before.board[cell].current_type_id != 'P' for cell in changed)
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/nonterminal_physical_support_20261003.json').read_text())
    for key in ('protocol_sha256', 'program_sha256', 'frame_sources_sha256', 'roots', 'materialized_transitions'):
        assert result[key] == recorded[key]
    for name, digest in result['frame_sources_sha256'].items():
        assert digest == hashlib.sha256((root / 'scripts' / name).read_bytes()).hexdigest()


def test_aborted_enumeration_is_not_zero_nonterminal_support():
    with pytest.raises(RuntimeError, match='transition cap'):
        audit(Budget(transitions_limit=1))
