"""Checkmate, stalemate, and mate-over-repetition priority."""

from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.core.attacks import is_in_check
from generic_chess.core.keys import position_key
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.position import GameState
from generic_chess.core.terminal import (
    TerminalResult,
    TerminalStatus,
    terminal_from_search_runtime,
    terminal_result,
)
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.native.compiler import NativeUnsupportedRuleError, build_compile_payload
from generic_chess.rules.compiler import compile_ruleset

from conftest import king_type, make_compiled, make_position, make_ruleset, T


def _compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    return make_compiled(8, [king_type(), rook])


def test_checkmate():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "r.......",
            "........",
            "........",
            "..k.....",
            "........",
            "K....r..",
        ],
        side_to_move=0,
    )
    assert is_in_check(pos, 0, compiled)
    assert legal_actions_from_position(pos, compiled) == []
    state = GameState(
        position=pos,
        ply_count=10,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.CHECKMATE
    assert result.winner == 1


def test_stalemate():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            ".....r..",
            "K.k.....",
        ],
        side_to_move=0,
    )
    assert not is_in_check(pos, 0, compiled)
    assert legal_actions_from_position(pos, compiled) == []
    state = GameState(
        position=pos,
        ply_count=10,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.STALEMATE
    assert result.winner is None


def test_stalemate_loss_policy_wins_for_opponent_in_all_terminal_paths():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    ruleset = replace(
        make_ruleset(8, [king_type(), rook]), stalemate_result="loss"
    )
    compiled = compile_ruleset(ruleset)
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            ".....r..",
            "K.k.....",
        ],
        side_to_move=0,
    )
    state = GameState(
        position=pos,
        ply_count=10,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )

    public_result = terminal_result(state, compiled)
    runtime = SearchPathRuntime.from_state(state, compiled)
    runtime_result = terminal_from_search_runtime(runtime)
    assert public_result == runtime_result
    assert public_result.status is TerminalStatus.STALEMATE
    assert public_result.winner == 1
    assert "player 1 wins" in str(public_result)
    assert terminal_score(public_result, side_to_move=0, ply=0) < 0
    assert terminal_score(public_result, side_to_move=1, ply=0) > 0


def test_native_payload_rejects_stalemate_loss_policy():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    compiled = compile_ruleset(
        replace(make_ruleset(8, [king_type(), rook]), stalemate_result="loss")
    )
    with pytest.raises(NativeUnsupportedRuleError, match="stalemate loss"):
        build_compile_payload(compiled)


def test_ongoing():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            ".......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "K.......",
        ],
    )
    state = GameState(
        position=pos,
        ply_count=0,
        repetition_counts=((position_key(pos, compiled), 1),),
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    assert terminal_result(state, compiled).status is TerminalStatus.ONGOING


def test_mate_takes_priority_over_repetition():
    compiled = _compiled()
    pos = make_position(
        compiled,
        [
            "........",
            "........",
            "r.......",
            "........",
            "........",
            "..k.....",
            "........",
            "K....r..",
        ],
        side_to_move=0,
    )
    key = position_key(pos, compiled)
    state = GameState(
        position=pos,
        ply_count=40,
        repetition_counts=((key, 4),),  # would be a repetition draw...
        terminal_status=TerminalResult(TerminalStatus.ONGOING),
    )
    result = terminal_result(state, compiled)
    assert result.status is TerminalStatus.CHECKMATE  # ...but mate wins
