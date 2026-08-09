from __future__ import annotations

import random

import pytest

from generic_chess.core.keys import semantic_position_key
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalStatus
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import candidate_perft, guarded_actions, make_checked, pack_action, pack_position, position_key, probe_search, snapshot

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


def _python_perft(semantic, position, depth):
    if depth == 0:
        return 1
    engine = SemanticEngine(semantic)
    actions = engine.legal_actions(position)
    if not actions:
        return 0
    return sum(_python_perft(semantic, engine.apply(position, action), depth - 1) for action in actions)


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_randomized_multi_fixture_closure():
    for name, semantic in semantic_corpus():
        native_rules = compile_native_semantic_rules(semantic)
        type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
        board = tuple(piece for row in semantic.support.initial_position for piece in row)
        engine = SemanticEngine(semantic)
        for seed in range(5):
            rng = random.Random((seed + 1) * 1009 + sum(ord(ch) for ch in name))
            python_position = Position(board, (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
            native_position = pack_position(native_rules, {
                "side": 0,
                "ply": 0,
                "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)] for piece in board],
                "hands": [[0] * len(type_ids), [0] * len(type_ids)],
                "aux_state": (),
            })
            for ply in range(10):
                python_actions = _packed_actions(semantic, python_position, native_rules)
                native_actions = set(guarded_actions(native_rules, native_position))
                assert set(python_actions) == native_actions, f"{name} seed={seed} ply={ply} action-set"
                python_key = semantic_position_key(python_position, semantic.support, semantic.ir.aux_slots)
                assert position_key(native_rules, native_position) == python_key, f"{name} seed={seed} ply={ply} key"
                terminal = engine.terminal_result(python_position, ply, ())
                native_probe = probe_search(native_rules, native_position, 1)
                if terminal.status is TerminalStatus.ONGOING:
                    assert native_probe["has_best"] == int(bool(native_actions)), f"{name} seed={seed} ply={ply} terminal"
                elif terminal.status is TerminalStatus.CHECKMATE:
                    assert native_probe["has_best"] == 0 and native_probe["score"] == -1_000_000, f"{name} seed={seed} ply={ply} checkmate"
                else:
                    assert native_probe["has_best"] == 0 and native_probe["score"] == 0, f"{name} seed={seed} ply={ply} terminal={terminal.status}"
                if not python_actions:
                    break
                chosen = rng.choice(sorted(python_actions))
                python_position = engine.apply(python_position, python_actions[chosen])
                native_position = make_checked(native_rules, native_position, chosen)
                observed = snapshot(native_rules, native_position)
                expected_board = [
                    None if piece is None else (type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted))
                    for piece in python_position.board
                ]
                assert observed["board"] == expected_board, f"{name} seed={seed} ply={ply} board action={chosen}"
                expected_hands = [
                    [dict(hand.counts).get(type_id, 0) for type_id in native_rules.type_ids]
                    for hand in python_position.hands
                ]
                assert observed["hands"] == expected_hands, f"{name} seed={seed} ply={ply} hands action={chosen}"
                assert observed["side"] == python_position.side_to_move
                assert observed["ply"] == ply + 1
                child_key = semantic_position_key(python_position, semantic.support, semantic.ir.aux_slots)
                assert position_key(native_rules, native_position) == child_key, f"{name} seed={seed} ply={ply} child-key action={chosen}"
                words = tuple(int(child_key[i:i + 16], 16) for i in range(0, 64, 16))
                assert observed["history"][-1] == words, f"{name} seed={seed} ply={ply} history action={chosen}"


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_perft_matches_python_on_full_corpus_depth_three():
    for name, semantic in semantic_corpus():
        native_rules = compile_native_semantic_rules(semantic)
        type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
        board = tuple(piece for row in semantic.support.initial_position for piece in row)
        python_position = Position(board, (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
        native_position = pack_position(native_rules, {
            "side": 0,
            "ply": 0,
            "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)] for piece in board],
            "hands": [[0] * len(type_ids), [0] * len(type_ids)],
            "aux_state": (),
        })
        assert candidate_perft(native_rules, native_position, 3) == _python_perft(semantic, python_position, 3), name


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_semantic_perft_depth_four_on_small_fixture():
    name, semantic = next((item for item in semantic_corpus() if item[0] == "weird_0"))
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = tuple(piece for row in semantic.support.initial_position for piece in row)
    python_position = Position(board, (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, int(piece.promoted)] for piece in board],
        "hands": [[0] * len(type_ids), [0] * len(type_ids)],
        "aux_state": (),
    })
    assert candidate_perft(native_rules, native_position, 4) == _python_perft(semantic, python_position, 4), name
