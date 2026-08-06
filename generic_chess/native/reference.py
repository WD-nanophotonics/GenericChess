"""Python Core reference helpers for native differential testing."""

from __future__ import annotations

import json

from ..core.actions import action_to_dict
from ..core.actions import BoardMove, DropMove
from ..core.coordinates import square_to_index
from ..core.terminal import TerminalStatus
from ..core.transition import apply_action, legal_successors
from ..ai.evaluation.config import MATE_SCORE


def python_legal_actions(state, compiled) -> list:
    return [action for action, _ in legal_successors(state, compiled)]


def python_perft(compiled, state, depth: int) -> int:
    if depth <= 0:
        return 1
    total = 0
    for _action, child in legal_successors(state, compiled):
        total += python_perft(compiled, child, depth - 1)
    return total


def canonical_action_set(actions) -> list[str]:
    return sorted(
        json.dumps(action_to_dict(a), sort_keys=True) for a in actions
    )


def python_child_snapshot(state, action, compiled) -> dict:
    child = apply_action(state, action, compiled)
    n = compiled.board_size
    board = []
    for piece in child.position.board:
        if piece is None:
            board.append(None)
        else:
            board.append(
                {
                    "base_type_id": piece.base_type_id,
                    "current_type_id": piece.current_type_id,
                    "owner": piece.owner,
                    "promoted": piece.promoted,
                }
            )
    hands = [
        dict(child.position.hands[owner].counts) for owner in (0, 1)
    ]
    from ..core.keys import position_key

    key = position_key(child.position, compiled)
    repetition_count = dict(child.repetition_counts).get(key, 0)
    return {
        "side_to_move": child.position.side_to_move,
        "ply": child.ply_count,
        "board": board,
        "hands": hands,
        "terminal": child.terminal_status.status.value,
        "repetition_count": repetition_count,
    }


def python_terminal(state) -> str:
    return state.terminal_status.status.value


def reference_terminal_score(terminal, side_to_move: int, ply: int) -> int:
    """Score of a terminal node from ``side_to_move``'s perspective."""
    if terminal.status in (
        TerminalStatus.STALEMATE,
        TerminalStatus.REPETITION,
        TerminalStatus.MAX_PLY,
    ):
        return 0
    if terminal.winner == side_to_move:
        return MATE_SCORE - ply
    return -MATE_SCORE + ply


def canonical_pack(compiled, state, action) -> int:
    """Pack a Core Action into the native layout using the same sorted type
    mapping the native compiler uses (numeric-ascending tie-break)."""
    n = compiled.board_size
    type_ids = sorted(compiled.types_by_id)
    type_map = {tid: i for i, tid in enumerate(type_ids)}
    if isinstance(action, DropMove):
        to = action.to_square.rank * n + action.to_square.file
        return (
            (to & 0xFF)
            | (0xFF << 8)
            | (0xFF << 16)
            | ((type_map[action.base_type_id] & 0xFF) << 24)
            | (1 << 32)
        )
    from_i = action.from_square.rank * n + action.from_square.file
    to_i = action.to_square.rank * n + action.to_square.file
    promo = (
        type_map[action.promotion_target_id]
        if action.promotion_target_id is not None
        else 0xFF
    )
    piece = state.position.board[square_to_index(action.from_square, n)]
    base = type_map[piece.base_type_id] if piece is not None else 0
    return (
        (to_i & 0xFF)
        | ((from_i & 0xFF) << 8)
        | ((promo & 0xFF) << 16)
        | ((base & 0xFF) << 24)
    )


def reference_fixed_depth_minimax(state, compiled, evaluator, depth: int, ply: int = 0):
    """Pure fixed-depth minimax oracle used only for differential testing.

    Returns ``(score, best_actions, canonical_best_action, pv, nodes)``:
    * ``score`` is in the root side-to-move perspective;
    * ``best_actions`` is the set of all actions achieving the best score;
    * ``canonical_best_action`` is the best action with the smallest packed
      native value (numeric ascending);
    * ``pv`` is the principal variation starting from the canonical action;
    * ``nodes`` counts every visited node (root, interior and leaves).
    No TT, no qsearch, no ordering heuristics, deterministic tie-break.
    """
    terminal = state.terminal_status
    if terminal.is_terminal:
        return (
            reference_terminal_score(terminal, state.position.side_to_move, ply),
            (),
            None,
            (),
            1,
        )
    if depth <= 0:
        return evaluator.evaluate(state), (), None, (), 1

    best = -10**12
    best_lines: list[tuple[int, object, tuple]] = []
    nodes = 1
    successors = sorted(
        legal_successors(state, compiled), key=lambda pair: str(pair[0])
    )
    for action, child in successors:
        child_score, _ba, _cb, child_pv, child_nodes = (
            reference_fixed_depth_minimax(
                child, compiled, evaluator, depth - 1, ply + 1
            )
        )
        nodes += child_nodes
        score = -child_score
        if score > best:
            best = score
            best_lines = [(canonical_pack(compiled, state, action), action, child_pv)]
        elif score == best:
            best_lines.append((canonical_pack(compiled, state, action), action, child_pv))

    best_actions = tuple(line[1] for line in best_lines)
    canonical = None
    pv: tuple = ()
    if best_lines:
        _packed, canonical, child_pv = min(best_lines, key=lambda line: line[0])
        pv = (canonical,) + child_pv
    return best, best_actions, canonical, pv, nodes
