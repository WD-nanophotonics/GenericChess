from __future__ import annotations

import pytest

from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import pack_action, pack_position, probe_search

from phase19c1_native_semantic_fixtures import semantic_corpus


def _packed_actions(semantic, position, native_rules):
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    geometry_ids = {geometry_id: index for index, geometry_id in enumerate(sorted(semantic.ir.geometry))}
    pattern_ids = {pattern.pattern_id: index for index, pattern in enumerate(semantic.ir.patterns)}
    result = {}
    for action in SemanticEngine(semantic).legal_actions(position):
        piece = position.board[action.source] if action.source is not None else None
        result[pack_action({
            "to": action.target,
            "from": action.source if action.source is not None else 255,
            "promotion": type_ids[action.promotion_target_id] if action.promotion_target_id else 255,
            "base": type_ids[piece.base_type_id] if piece is not None else type_ids[action.actor_type],
            "kind": 2 if action.source is not None else 3,
            "pattern": pattern_ids[action.pattern_id],
            "geometry": geometry_ids[action.geometry_id],
            "actor_current": type_ids[action.actor_type],
        })] = action
    return result


def _python_probe(semantic, position, native_rules, depth):
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    engine = SemanticEngine(semantic)
    nodes = 1

    def evaluate(state):
        return sum(
            (type_ids[piece.base_type_id] + 1) * (1 if piece.owner == state.side_to_move else -1)
            for piece in state.board
            if piece is not None
        )

    def search(state, remaining):
        nonlocal nodes
        if remaining == 0:
            return evaluate(state), ()
        actions = _packed_actions(semantic, state, native_rules)
        best_score = evaluate(state)
        best_action = None
        best_pv = ()
        for packed in sorted(actions):
            nodes += 1
            score, child_pv = search(engine.apply(state, actions[packed]), remaining - 1)
            score = -score
            if best_action is None or score > best_score or (score == best_score and packed < best_action):
                best_score, best_action = score, packed
                best_pv = (packed,) + child_pv
        return best_score, best_pv

    score, pv = search(position, depth)
    best = pv[0] if pv else None
    return {"score": score, "principal_variation": pv, "best_action": best, "has_best": int(best is not None), "nodes": nodes}


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_probe_search_matches_python_minimax_on_semantic_corpus():
    for name, semantic in semantic_corpus():
        native_rules = compile_native_semantic_rules(semantic)
        board = tuple(piece for row in semantic.support.initial_position for piece in row)
        python_position = Position(board, (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
        type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
        native_board = [
            None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)]
            for piece in board
        ]
        native_position = pack_position(native_rules, {
            "side": 0,
            "ply": 0,
            "board": native_board,
            "hands": [[0] * len(type_ids), [0] * len(type_ids)],
            "aux_state": (),
        })
        expected = _python_probe(semantic, python_position, native_rules, 2)
        observed = probe_search(native_rules, native_position, 2)
        assert observed == expected, name
