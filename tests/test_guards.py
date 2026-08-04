"""Regression tests for v0 correctness hardening (one per review finding)."""

import json

import pytest

from generic_chess import IllegalActionError, RuleSetMismatchError
from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from generic_chess.core.coordinates import is_forward_relative
from generic_chess.core.errors import ensure_ruleset_match
from generic_chess.core.keys import position_key
from generic_chess.core.movegen import (
    _apply_action_unchecked,
    legal_actions,
    legal_actions_from_position,
)
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.position import Hands
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.generation.config import GenerationError, GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.validation import RuleValidationError

from conftest import king_type, make_compiled, make_position, make_state, sq, T


def _rook_compiled():
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    return make_compiled(8, [king_type(), rook])


def _rook_board():
    return [
        "K......k",  # rank 7
        "........",
        "........",
        "........",
        "........",
        "........",
        "........",
        "...R....",  # rank 0
    ]


def test_illegal_board_move_rejected_and_state_unchanged():
    compiled = _rook_compiled()
    filler = T("F", LeapAtom((1, 0)))
    compiled = make_compiled(8, [king_type(), T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0))), filler])
    state = make_state(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "...F....",  # rank 1 blocker
            "...R....",  # rank 0
        ],
    )
    forged = BoardMove(sq(3, 0), sq(3, 3))  # jumps over the friendly blocker
    assert forged not in legal_actions_from_position(state.position, compiled)
    original_board = state.position.board
    with pytest.raises(IllegalActionError):
        apply_action(state, forged, compiled)
    assert state.position.board == original_board  # immutable: nothing mutated


def test_out_of_bounds_action_rejected():
    compiled = _rook_compiled()
    state = make_state(compiled, _rook_board())
    with pytest.raises(IllegalActionError):
        apply_action(state, BoardMove(sq(-1, 0), sq(0, 0)), compiled)
    with pytest.raises(IllegalActionError):
        _apply_action_unchecked(state.position, BoardMove(sq(3, 0), sq(3, 8)), compiled)


def _pawn_compiled():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    return make_compiled(8, [king_type(), pawn, gold], auto_promotion=True)


def _pawn_board():
    return [
        ".......k",
        "....P...",
        "........",
        "........",
        "........",
        "........",
        "........",
        "K.......",
    ]


def test_forged_promotion_to_anchor_rejected():
    compiled = _pawn_compiled()
    state = make_state(compiled, _pawn_board())
    forged = BoardMove(sq(4, 6), sq(4, 7), "K")
    with pytest.raises(IllegalActionError):
        apply_action(state, forged, compiled)
    with pytest.raises(IllegalActionError):
        _apply_action_unchecked(state.position, forged, compiled)
    # No second anchor can ever appear.
    anchors = [
        p
        for p in state.position.board
        if p is not None and compiled.types_by_id[p.current_type_id].is_anchor
    ]
    assert len(anchors) == 2


def test_forged_promotion_to_unknown_target_rejected():
    compiled = _pawn_compiled()
    state = make_state(compiled, _pawn_board())
    forged = BoardMove(sq(4, 6), sq(4, 7), "Z")
    with pytest.raises(IllegalActionError):
        apply_action(state, forged, compiled)


def test_forged_promotion_to_valid_target_accepted():
    compiled = _pawn_compiled()
    state = make_state(compiled, _pawn_board())
    legal = BoardMove(sq(4, 6), sq(4, 7), "G")
    after = apply_action(state, legal, compiled)
    piece = after.position.board[7 * 8 + 4]
    assert piece.promoted and piece.current_type_id == "G" and piece.base_type_id == "P"


def test_fingerprint_mismatch_raises_on_all_public_entries():
    game_a = generate_game(GeneratorConfig(seed=2026))
    game_b = generate_game(GeneratorConfig(seed=2027))
    compiled_a = game_a.compiled_ruleset
    compiled_b = game_b.compiled_ruleset
    state = initial_state(compiled_a)
    pos = state.position
    action = legal_actions_from_position(pos, compiled_a)[0]

    with pytest.raises(RuleSetMismatchError):
        legal_actions(state, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        legal_actions_from_position(pos, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        pseudo_attacks(pos, 0, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        is_square_attacked(pos, sq(0, 0), 0, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        is_in_check(pos, 0, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        terminal_result(state, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        position_key(pos, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        apply_action(state, action, compiled_b)
    with pytest.raises(RuleSetMismatchError):
        ensure_ruleset_match(pos, compiled_b)


def test_overlapping_atoms_deduplicated_and_order_stable():
    overlap = T("O", LeapAtom((0, 1)), RayAtom((0, 1), max_steps=1))
    compiled = make_compiled(8, [king_type(), overlap])
    pos = make_position(
        compiled,
        [
            "K......k",
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "O.......",
        ],
    )
    first = legal_actions_from_position(pos, compiled)
    second = legal_actions_from_position(pos, compiled)
    b2b3 = [a for a in first if a.from_square == sq(0, 0) and a.to_square == sq(0, 1)]
    assert len(b2b3) == 1
    assert first == second  # stable order and deduped


def test_schema_version_rejected():
    from conftest import make_ruleset

    ruleset = make_ruleset(8, [king_type(), T("R", RayAtom((0, 1)))])
    data = ruleset_to_dict(ruleset)
    data["schema_version"] = 999
    with pytest.raises(RuleValidationError) as exc:
        compile_ruleset(data)
    assert any(i.code == "SCHEMA_VERSION_UNSUPPORTED" for i in exc.value.issues)


def _valid_ruleset_dict() -> dict:
    from conftest import make_ruleset

    rook = T("R", RayAtom((0, 1)))
    return ruleset_to_dict(make_ruleset(8, [king_type(), rook]))


def test_owner_two_reports_validation_error_not_keyerror():
    data = _valid_ruleset_dict()
    data["initial_position"][0][0]["owner"] = 2
    with pytest.raises(RuleValidationError) as exc:
        compile_ruleset(data)
    assert any(i.code == "ILLEGAL_OWNER" for i in exc.value.issues)


def test_string_false_is_not_silently_true():
    data = _valid_ruleset_dict()
    data["piece_types"][0]["is_anchor"] = "false"
    with pytest.raises(RuleValidationError):
        compile_ruleset(data)


def test_wrong_field_types_raise_structured_errors():
    data = _valid_ruleset_dict()
    data["board_size"] = "8"
    with pytest.raises(RuleValidationError):
        compile_ruleset(data)

    data = _valid_ruleset_dict()
    del data["board_size"]
    with pytest.raises(RuleValidationError) as exc:
        compile_ruleset(data)
    assert any(i.code == "MISSING_FIELD" for i in exc.value.issues)


def test_bad_json_wrapped_as_validation_error():
    with pytest.raises(RuleValidationError) as exc:
        deserialize_ruleset("{not json")
    assert any(i.code == "INVALID_JSON" for i in exc.value.issues)


def test_hands_iterable():
    h = Hands((("P", 2), ("G", 1)))
    assert list(h) == [("P", 2), ("G", 1)]
    assert dict(h) == {"P": 2, "G": 1}


def test_is_forward_relative_owner_frame():
    # Owner-relative coordinates: dr > 0 is forward for both players.
    assert is_forward_relative((1, 1), 0)
    assert is_forward_relative((1, 1), 1)
    assert not is_forward_relative((1, -1), 0)
    assert not is_forward_relative((1, -1), 1)


def test_generator_rejects_3x3():
    with pytest.raises(GenerationError):
        generate_game(GeneratorConfig(seed=5, board_size=3))


def test_allow_hybrid_functional_and_deterministic():
    hybrid = generate_game(GeneratorConfig(seed=2, allow_hybrid=True))
    pure = generate_game(GeneratorConfig(seed=2, allow_hybrid=False))
    again = generate_game(GeneratorConfig(seed=2, allow_hybrid=True))
    assert again.compiled_ruleset.ruleset_fingerprint == hybrid.compiled_ruleset.ruleset_fingerprint
    assert hybrid.compiled_ruleset.ruleset_fingerprint != pure.compiled_ruleset.ruleset_fingerprint

    def kinds_of(game):
        result = {}
        for pt in game.ruleset.piece_types:
            if pt.is_anchor:
                continue
            result[pt.type_id] = {
                "leap": any(isinstance(a, LeapAtom) for a in pt.movement_atoms),
                "ray": any(isinstance(a, RayAtom) for a in pt.movement_atoms),
            }
        return result

    hybrid_kinds = kinds_of(hybrid)
    pure_kinds = kinds_of(pure)
    assert any(v["leap"] and v["ray"] for v in hybrid_kinds.values())  # real hybrids
    assert all(v["leap"] != v["ray"] for v in pure_kinds.values())  # pure types only


def test_apply_action_on_terminal_state_rejected():
    down_ray = T("R", RayAtom((0, -1)))
    compiled = make_compiled(8, [king_type(), down_ray])
    state = make_state(
        compiled,
        [
            "........",
            "........",
            "........",
            "........",
            "........",
            "........",
            "..K.....",
            "k.......",
        ],
        side_to_move=0,
        hands=([("R", 1)], []),
    )
    mate = apply_action(state, DropMove("R", sq(0, 3)), compiled)
    assert mate.terminal_status.is_terminal
    with pytest.raises(IllegalActionError):
        apply_action(mate, DropMove("R", sq(1, 1)), compiled)


def test_errors_exported_from_public_api():
    import generic_chess as gc

    assert gc.IllegalActionError is IllegalActionError
    assert gc.RuleSetMismatchError is RuleSetMismatchError
