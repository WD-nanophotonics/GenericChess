"""Phase 2C-1: repetition-context fingerprint (incremental == rebuild,
history isolation, completeness flag)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.native.adapter import (
    native_long_make_unmake_roundtrip,
    native_snapshot,
    pack_native_position,
    pack_native_search_position,
)
from generic_chess.native.compiler import compile_native_rules

from native_test_helpers import generated_compiled, make_state, requires_native


@requires_native
def test_replay_context_incremental_matches_rebuild():
    from generic_chess.session.session import GameSession

    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 11)
    rules = compile_native_rules(compiled)
    # The C replay verifies incremental context == rebuild after every ply.
    result = native_long_make_unmake_roundtrip(compiled, rules, session)
    assert result["ok"] == 1
    assert result["steps"] == 11
    pos = pack_native_search_position(compiled, rules, session)
    snapshot = native_snapshot(rules, pos)
    assert snapshot["history_complete"] == 1


@requires_native
def test_same_board_different_history_contexts_differ():
    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    rules = compile_native_rules(compiled)
    snaps = []
    for ply in (3, 7, 11):
        session = _session_at_ply(compiled, ply)
        pos = pack_native_search_position(compiled, rules, session)
        snaps.append(native_snapshot(rules, pos))
    # plies 3 and 11 share the same board/hand/side (4-cycle).
    assert snaps[0]["hash_lo"] == snaps[2]["hash_lo"]
    assert snaps[0]["hash_hi"] == snaps[2]["hash_hi"]
    contexts = {
        (s["repetition_context_lo"], s["repetition_context_hi"]) for s in snaps
    }
    assert len(contexts) == 3


@requires_native
def test_legacy_pack_is_marked_incomplete():
    compiled = generated_compiled(size=4)
    rules = compile_native_rules(compiled)
    state = make_state(compiled, compiled.initial_position)
    pos = pack_native_position(compiled, rules, state)
    snapshot = native_snapshot(rules, pos)
    assert snapshot["history_complete"] == 0
    # Full replay is marked complete.
    from generic_chess.session.session import GameSession

    session = GameSession(compiled)
    pos2 = pack_native_search_position(compiled, rules, session)
    snapshot2 = native_snapshot(rules, pos2)
    assert snapshot2["history_complete"] == 1


@requires_native
def test_unmake_restores_context():
    from generic_chess.native.adapter import (
        native_legal_actions,
        native_make_unmake_roundtrip,
    )
    from generic_chess.session.session import GameSession

    from test_native_history import _cycle_ruleset, _session_at_ply

    compiled = _cycle_ruleset()
    session = _session_at_ply(compiled, 11)
    rules = compile_native_rules(compiled)
    pos = pack_native_search_position(compiled, rules, session)
    action = native_legal_actions(rules, pos)[0]
    check = native_make_unmake_roundtrip(rules, pos, action)
    assert check["make_ok"] == 1
    assert check["hash_restored_ok"] == 1
    assert check["state_restored"] == 1
