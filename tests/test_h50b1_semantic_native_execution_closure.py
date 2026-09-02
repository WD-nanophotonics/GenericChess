from __future__ import annotations

from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    assess_declaration,
    available_declarations,
    guarded_actions,
    pack_action,
    pack_position,
    position_key,
    public_action,
    terminal_status,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


def _initial(semantic, native):
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id], ids[piece.current_type_id],
            piece.owner, int(piece.promoted),
        ]
        for row in semantic.support.initial_position
        for piece in row
    ]
    return pack_position(native, {
        "side": 0,
        "ply": 0,
        "board": board,
        "hands": [[0] * len(ids), [0] * len(ids)],
        "aux_state": (),
    })


def test_h50b1_western_exact_initial_action_identity_and_max_ply():
    semantic = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(semantic)
    position = _initial(semantic, native)

    actions = guarded_actions(native, position)
    assert len(actions) == 20
    for packed in actions:
        public = public_action(native, packed)
        fields = {
            "to": public.to_square.rank * semantic.support.board_size + public.to_square.file,
            "from": public.from_square.rank * semantic.support.board_size + public.from_square.file,
            "promotion": 255,
            "base": native.type_ids.index(public.actor_type_id),
            "kind": 2,
            "pattern": native.pattern_ids.index(public.pattern_id),
            "geometry": native.geometry_ids.index(public.geometry_id),
            "actor_current": native.type_ids.index(public.actor_type_id),
        }
        assert pack_action(fields) == packed
    assert semantic.support.max_ply == 1000
    assert native.report.native_executable
    assert position_key(native, position)


def test_h50b1_shogi_declarations_continuous_check_and_adjudication():
    semantic = compile_semantic_ruleset(build_standard_shogi_ruleset())
    native = compile_native_semantic_rules(semantic)
    position = _initial(semantic, native)
    assert native.repetition_policy == "continuous_check_loss"
    assert len(native.declarations) == 2
    assert available_declarations(native, position) == ()
    assessment = assess_declaration(native, position, "claim_owner_0")
    assert assessment.actor == 0
    assert assessment.outcome == "LOSS"
    assert assessment.weighted_score is not None

    digest = position_key(native, position)
    words = tuple(int(digest[i:i + 16], 16) for i in range(0, 64, 16))
    repeated = pack_position(native, {
        "side": 0,
        "ply": 0,
        "board": [
            None if piece is None else [
                native.type_ids.index(piece.base_type_id),
                native.type_ids.index(piece.current_type_id),
                piece.owner, int(piece.promoted),
            ]
            for row in semantic.support.initial_position
            for piece in row
        ],
        "hands": [[0] * len(native.type_ids), [0] * len(native.type_ids)],
        "history": [words] * 5,
        "history_events": [(255, 0), (0, 1), (1, 0), (0, 1), (1, 0)],
        "aux_state": (),
    })
    assert terminal_status(native, repeated) == {
        "status": "perpetual_check", "winner": 1,
    }

    incomplete_at_five_hundred = pack_position(native, {
        "side": 0,
        "ply": 500,
        "board": [
            None if piece is None else [
                native.type_ids.index(piece.base_type_id),
                native.type_ids.index(piece.current_type_id),
                piece.owner, int(piece.promoted),
            ]
            for row in semantic.support.initial_position
            for piece in row
        ],
        "hands": [[0] * len(native.type_ids), [0] * len(native.type_ids)],
        "aux_state": (),
    })
    import pytest

    with pytest.raises(ValueError, match="exact full history"):
        terminal_status(native, incomplete_at_five_hundred)

    full_history = [tuple((i + 1) * (j + 3) for j in range(4)) for i in range(500)]
    full_history.append(words)
    full_events = [(255, 0)] + [(i % 2, 0) for i in range(500)]
    at_five_hundred = pack_position(native, {
        "side": 0,
        "ply": 500,
        "board": [
            None if piece is None else [
                native.type_ids.index(piece.base_type_id),
                native.type_ids.index(piece.current_type_id),
                piece.owner, int(piece.promoted),
            ]
            for row in semantic.support.initial_position
            for piece in row
        ],
        "hands": [[0] * len(native.type_ids), [0] * len(native.type_ids)],
        "history": full_history,
        "history_events": full_events,
        "aux_state": (),
    })
    assert terminal_status(native, at_five_hundred)["status"] == "no_contest"


def test_h50b1_generic_compiler_witness_keeps_exact_semantic_identity():
    from rule_semantics_ir_fixtures import cannon_ruleset

    semantic = compile_semantic_ruleset(cannon_ruleset())
    native = compile_native_semantic_rules(semantic)
    position = _initial(semantic, native)
    actions = guarded_actions(native, position)
    assert actions
    for packed in actions:
        public = public_action(native, packed)
        assert public.pattern_id in native.pattern_ids
        assert public.geometry_id in native.geometry_ids
        assert public.to_square.file >= 0
