"""Legacy captures honor custody semantics, including promoted base identity."""
from dataclasses import replace

import pytest

from conftest import T, king_type, make_ruleset
from generic_chess.core.actions import BoardMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.search_runtime import SearchPathRuntime, _full_runtime_hash
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError, build_compile_payload, compile_native_rules,
)
from generic_chess.rules.compiler import compile_ruleset_for_execution


def capture_fixture(disposition, owner=0):
    types = [king_type(), T("R", RayAtom((0, 1)), RayAtom((0, -1))),
             T("P", LeapAtom((0, 1)), is_promotable=True, targets=("R",))]
    rules = make_ruleset(8, types)
    board = [[None] * 8 for _ in range(8)]
    board[0][0] = Piece(0, "K", "K")
    board[7][7] = Piece(1, "K", "K")
    board[3][3] = Piece(owner, "R", "R")
    board[4][3] = Piece(1 - owner, "P", "R", promoted=True)
    return compile_ruleset_for_execution(replace(
        rules, initial_position=tuple(map(tuple, board)),
        capture_disposition=disposition,
    ))


@pytest.mark.parametrize("disposition", ["capture_to_hand", "remove_from_game"])
@pytest.mark.parametrize("owner", [0, 1])
def test_legacy_promoted_capture_public_and_search_path(disposition, owner):
    compiled = capture_fixture(disposition, owner)
    root = initial_state(compiled)
    # Import a legal owner-one root with consistent public history/identity.
    if owner:
        from generic_chess.core.identity import repetition_identity_key
        from generic_chess.core.position import HistoryRecord
        position = replace(root.position, side_to_move=owner)
        key = repetition_identity_key(position, compiled)
        root = replace(root, position=position, repetition_counts=((key, 1),),
                       history=(HistoryRecord(key, -1, "", False),))
    action = BoardMove(Square(3, 3), Square(3, 4))
    child = apply_action(root, action, compiled)
    assert child.position.board[3 + 4 * 8] == Piece(owner, "R", "R")
    assert child.position.hands[owner].count("P") == (disposition == "capture_to_hand")
    assert child.position.hands[owner].count("R") == 0
    assert child.position.hands[1 - owner].total() == 0
    runtime = SearchPathRuntime.from_state(root, compiled)
    root_hash = runtime.runtime_hash
    with runtime.pushed(action):
        assert runtime.position == child.position
        assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
        for reply in runtime.legal_actions():
            expected = apply_action(child, reply, compiled)
            with runtime.pushed(reply):
                assert runtime.position == expected.position
                assert runtime.runtime_hash == _full_runtime_hash(runtime.position, compiled)
    runtime.assert_balanced()
    assert runtime.position == root.position
    assert runtime.runtime_hash == root_hash


def test_legacy_native_rejects_unsupported_custody_before_loading(monkeypatch):
    compiled = capture_fixture("remove_from_game")
    def unexpected_load():
        pytest.fail("unsupported legacy disposition must not load a native module")
    monkeypatch.setattr("generic_chess.native.compiler.native_available", unexpected_load)
    for entry in (build_compile_payload, compile_native_rules):
        with pytest.raises(NativeUnsupportedRuleError, match="remove_from_game"):
            entry(compiled)


def test_legacy_native_default_payload_stays_supported():
    payload, report = build_compile_payload(capture_fixture("capture_to_hand"))
    assert payload and report.type_count == 3
