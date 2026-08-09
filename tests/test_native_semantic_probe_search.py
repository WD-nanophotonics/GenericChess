from __future__ import annotations

import pytest

from generic_chess.core.position import Hands, Position
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.core.terminal import TerminalStatus
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import pack_action, pack_position, probe_search
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleActionEffect, RuleGeometrySpec, RuleSemanticAction, RuleSet, RuleSquareRef

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


def _python_probe(semantic, position, native_rules, depth, board_values=None, hand_values=None):
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    engine = SemanticEngine(semantic)
    nodes = 1

    def evaluate(state):
        return sum(
            (board_values[type_ids[piece.base_type_id]] if board_values is not None else type_ids[piece.base_type_id] + 1) * (1 if piece.owner == state.side_to_move else -1)
            for piece in state.board
            if piece is not None
        ) + sum(
            count * (hand_values[type_ids[type_id]] if hand_values is not None else type_ids[type_id] + 1) * (1 if owner == state.side_to_move else -1)
            for owner, hand in enumerate(state.hands)
            for type_id, count in hand.counts
        )

    def search(state, remaining, ply=0, alpha=-1_000_000_000, beta=1_000_000_000):
        nonlocal nodes
        terminal = engine.terminal_result(state, ply, ())
        if terminal.status is TerminalStatus.CHECKMATE:
            return -1_000_000, ()
        if terminal.status is not TerminalStatus.ONGOING:
            return 0, ()
        if remaining == 0:
            return evaluate(state), ()
        actions = _packed_actions(semantic, state, native_rules)
        best_score = -1_000_000_000
        best_action = None
        best_pv = ()
        for packed in sorted(actions):
            nodes += 1
            score, child_pv = search(engine.apply(state, actions[packed]), remaining - 1, ply + 1, -beta, -alpha)
            score = -score
            if best_action is None or score > best_score or (score == best_score and packed < best_action):
                best_score, best_action = score, packed
                best_pv = (packed,) + child_pv
            alpha = max(alpha, score)
            if alpha >= beta:
                break
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
        expected = _python_probe(semantic, python_position, native_rules, 3)
        observed = probe_search(native_rules, native_position, 3)
        assert observed == expected, name


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_probe_search_depth_zero_is_deterministic_leaf():
    semantic = next(semantic for name, semantic in semantic_corpus() if name == "castling")
    native_rules = compile_native_semantic_rules(semantic)
    board = tuple(piece for row in semantic.support.initial_position for piece in row)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board],
        "hands": [[0] * len(type_ids), [0] * len(type_ids)],
        "aux_state": (),
    })
    observed = probe_search(native_rules, native_position, 0)
    assert observed["nodes"] == 1
    assert observed["has_best"] == 0
    assert observed["best_action"] is None
    assert observed["principal_variation"] == ()


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
@pytest.mark.parametrize("fixture_name", ["nifu", "uchifuzume"])
def test_native_probe_search_matches_python_on_drop_and_s4_positions(fixture_name):
    from rule_semantics_ir_fixtures import nifu_ruleset, uchifuzume_ruleset

    ruleset = nifu_ruleset() if fixture_name == "nifu" else uchifuzume_ruleset()
    semantic = compile_semantic_ruleset(ruleset)
    native_rules = compile_native_semantic_rules(semantic)
    board = tuple(piece for row in semantic.support.initial_position for piece in row)
    python_position = Position(board, (Hands((("P", 1),)), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_hands = [[0] * len(type_ids), [0] * len(type_ids)]
    native_hands[0][type_ids["P"]] = 1
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board],
        "hands": native_hands,
        "aux_state": (),
    })
    expected = _python_probe(semantic, python_position, native_rules, 2)
    observed = probe_search(native_rules, native_position, 2)
    assert observed == expected, fixture_name


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_probe_search_accepts_stable_board_and_hand_profile():
    from rule_semantics_ir_fixtures import nifu_ruleset

    semantic = compile_semantic_ruleset(nifu_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    board = tuple(piece for row in semantic.support.initial_position for piece in row)
    python_position = Position(board, (Hands((("P", 1),)), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_hands = [[0] * len(type_ids), [0] * len(type_ids)]
    native_hands[0][type_ids["P"]] = 1
    native_position = pack_position(native_rules, {"side": 0, "ply": 0, "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board], "hands": native_hands, "aux_state": ()})
    board_values = [3 + i for i in range(len(type_ids))]
    hand_values = [11 + 2 * i for i in range(len(type_ids))]
    expected = _python_probe(semantic, python_position, native_rules, 2, board_values, hand_values)
    observed = probe_search(native_rules, native_position, 2, board_values=board_values, hand_values=hand_values)
    assert observed == expected


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_probe_search_rejects_partial_or_malformed_profile():
    from rule_semantics_ir_fixtures import nifu_ruleset

    semantic = compile_semantic_ruleset(nifu_ruleset())
    native_rules = compile_native_semantic_rules(semantic)
    board = tuple(piece for row in semantic.support.initial_position for piece in row)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board],
        "hands": [[0] * len(type_ids), [0] * len(type_ids)],
        "aux_state": (),
    })
    with pytest.raises(ValueError, match="supplied together"):
        probe_search(native_rules, native_position, 1, board_values=[1] * len(type_ids))
    with pytest.raises(ValueError, match="length"):
        probe_search(native_rules, native_position, 1, board_values=[1], hand_values=[1])
    with pytest.raises(ValueError, match="bounded"):
        probe_search(native_rules, native_position, 1, board_values=[1] * len(type_ids), hand_values=[1_000_001] * len(type_ids))


@pytest.mark.skipif(not native_available(), reason="native extension unavailable")
def test_native_probe_search_matches_python_on_promotion_position():
    from rule_semantics_ir_fixtures import _king_type

    n = 5
    pawn = PieceType("P", "P", (LeapAtom((0, 1)),), is_promotable=True, promotion_target_ids=("G",))
    gold = PieceType("G", "G", (LeapAtom((1, 0)),))
    action = RuleSemanticAction(
        name="promotion_move",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="legacy_atoms", atom_kind="leap"),
        target_relation="empty",
        effects=(RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target")),),
        promotion_mode="inherit_compiled_masks",
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    source, target = Square(1, 1), Square(1, 2)
    ruleset = RuleSet(
        board_size=n,
        piece_types=(_king_type(), pawn, gold),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"P": ((False,) * 25, (False,) * 25), "G": ((False,) * 25, (False,) * 25)},
        promotion_allowed={"P": (frozenset({(source, target)}), frozenset({(source, target)}))},
        promotion_forced={"P": (frozenset(), frozenset())},
        semantic_actions=(action,),
    )
    semantic = compile_semantic_ruleset(ruleset)
    board = list(rows[0] + rows[1] + rows[2] + rows[3] + rows[4])
    board[source.rank * n + source.file] = Piece(0, "P", "P")
    python_position = Position(tuple(board), (Hands.empty(), Hands.empty()), 0, semantic.support.ruleset_fingerprint)
    native_rules = compile_native_semantic_rules(semantic)
    type_ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    native_position = pack_position(native_rules, {
        "side": 0,
        "ply": 0,
        "board": [None if piece is None else [type_ids[piece.base_type_id], type_ids[piece.current_type_id], piece.owner, 0] for piece in board],
        "hands": [[0] * len(type_ids), [0] * len(type_ids)],
        "aux_state": (),
    })
    assert probe_search(native_rules, native_position, 2) == _python_probe(semantic, python_position, native_rules, 2)
