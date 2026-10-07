from __future__ import annotations

import pytest

from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import guarded_actions, make_checked, pack_action, pack_position

from phase19c1_native_semantic_fixtures import semantic_corpus


def _packed_actions(semantic, position, native_rules):
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    geometry_ids = {geometry_id: index for index, geometry_id in enumerate(sorted(semantic.ir.geometry))}
    pattern_ids = {pattern.pattern_id: index for index, pattern in enumerate(semantic.ir.patterns)}
    packed = {}
    for action in SemanticEngine(semantic).legal_actions(position):
        piece = position.board[action.source] if action.source is not None else None
        base = type_ids[piece.base_type_id] if piece is not None else type_ids[action.actor_type]
        packed[pack_action({
            "to": action.target,
            "from": action.source if action.source is not None else 255,
            "promotion": type_ids[action.promotion_target_id] if action.promotion_target_id else 255,
            "base": base,
            "kind": 2 if action.source is not None else 3,
            "pattern": pattern_ids[action.pattern_id],
            "geometry": geometry_ids[action.geometry_id],
            "actor_current": type_ids[action.actor_type],
        })] = action
    return packed


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_stress_corpus_has_exact_eight_ply_differential():
    for name, semantic in semantic_corpus():
        native_rules = compile_native_semantic_rules(semantic)
        board = tuple(piece for row in semantic.support.initial_position for piece in row)
        python_position = Position(
            board,
            (Hands.empty(), Hands.empty()),
            0,
            semantic.support.ruleset_fingerprint,
        )
        type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
        native_board = [
            None
            if piece is None
            else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)]
            for piece in board
        ]
        native_position = pack_position(
            native_rules,
            {
                "side": 0,
                "ply": 0,
                "board": native_board,
                "hands": [[0] * len(type_ids), [0] * len(type_ids)],
                "aux_state": (),
            },
        )
        engine = SemanticEngine(semantic)
        for ply in range(8):
            python_actions = _packed_actions(semantic, python_position, native_rules)
            native_actions = set(guarded_actions(native_rules, native_position))
            assert set(python_actions) == native_actions, name + f" ply={ply}"
            if not python_actions:
                break
            chosen = min(python_actions)
            python_position = engine.apply(python_position, python_actions[chosen])
            native_position = make_checked(native_rules, native_position, chosen)
