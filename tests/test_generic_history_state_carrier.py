"""Direct contract for the immutable, game-agnostic history carrier."""

import json
from dataclasses import FrozenInstanceError

import pytest

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.history_provenance import reconstruct_history_provenance
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import HistoryRecord
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset


@pytest.mark.parametrize(
    "build_ruleset",
    (
        build_western_chess_ruleset,
        build_standard_shogi_ruleset,
        build_xiangqi_diagnostic_ruleset,
    ),
    ids=("western-chess", "standard-shogi", "xiangqi"),
)
def test_one_legal_transition_preserves_generic_history_carrier(build_ruleset):
    compiled = compile_ruleset_for_execution(build_ruleset())
    before = initial_state(compiled)
    action = legal_actions(before, compiled)[0]

    after = apply_action(before, action, compiled)

    assert isinstance(after.history, tuple)
    assert after.history[:-1] == before.history
    record = after.history[-1]
    assert isinstance(record, HistoryRecord)
    assert record.position_key == repetition_identity_key(after.position, compiled)
    assert record.actor == before.position.side_to_move
    assert record.action_signature == json.dumps(
        action_to_dict(action), sort_keys=True, separators=(",", ":")
    )
    assert isinstance(record.gave_check, bool)
    with pytest.raises(FrozenInstanceError):
        record.actor = 1 - record.actor
    assert reconstruct_history_provenance(after, compiled).status == "verified"
