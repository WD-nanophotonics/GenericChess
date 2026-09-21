"""Gate 1: differential benchmark of GenericChess and known-game backends.

This is deliberately a benchmark-only harness.  It gives GenericChess and
python-chess/cshogi the same fixed material evaluator, canonical move order,
and small negamax/alpha-beta search, then stops at the first hard fork.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chess
import cshogi

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import GameState
from generic_chess.core.terminal import TerminalResult, TerminalStatus, terminal_result
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from scripts.audit_f24f_western_chess_perft import compiled_western_chess, position_from_fen


MATE_SCORE = 100_000
INF = 1_000_000

CHESS_MATERIAL = {"K": 0, "P": 100, "N": 320, "B": 330, "R": 500, "Q": 900}
SHOGI_MATERIAL = {
    "K": 0, "P": 100, "L": 300, "N": 300, "S": 400, "G": 500,
    "B": 800, "R": 1_000, "TP": 600, "TL": 600, "TN": 600,
    "TS": 600, "TB": 1_100, "TR": 1_300,
    "+P": 600, "+L": 600, "+N": 600, "+S": 600, "+B": 1_100, "+R": 1_300,
}

CHESS_POSITIONS = (
    ("initial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
    ("position-3", "8/2p5/3p4/KP5r/1R3p1k/8/8/8 w - - 0 1"),
    ("position-4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"),
    ("position-5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"),
    ("position-6", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"),
    ("kings", "4k3/8/8/8/8/8/8/4K3 w - - 0 1"),
    ("pawn-race", "4k3/8/8/3P4/8/8/8/4K3 w - - 0 1"),
    ("castling", "4k2r/P7/8/8/8/8/8/R3K2R w Kq - 0 1"),
    ("promotion", "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"),
    ("checkmate", "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"),
    ("stalemate", "7k/5Q2/5K2/8/8/8/8/8 b - - 0 1"),
)
CHESS_LOW_BRANCH = frozenset({"kings", "pawn-race", "castling", "promotion"})

SHOGI_POSITIONS = (
    ("descriptor-1", "lnsgkgsnl/2r4b1/pp1pp1ppp/2p6/5p3/5PP2/PPPPP1NPP/1B2G3R/LNS1KGS1L b - 13"),
    ("descriptor-2", "lns4nl/1r1gksgb1/pp1p1pppp/2p1p4/9/1P4P2/P1PPPPNPP/1B2G1SR1/LNS1KG2L b - 13"),
    ("descriptor-3", "ln1gkgsnl/1s4rb1/1p1pppp1p/p1p4p1/9/P2P1P3/1PP1P1PPP/LB2R4/1NSGKGSNL b - 13"),
    ("descriptor-4", "1nsgkg1n1/l4srb1/ppp1ppppl/3p4p/9/3P5/PPP1PPPPP/1B3G2R/LNSGK1SNL b - 13"),
    ("descriptor-5", "1nsg2gnl/l2rk1sb1/pppppp1pp/6p2/9/P4P2P/1PPPP1PP1/1B1G1GSR1/LNS1K2NL b - 13"),
    ("descriptor-6", "ln1gkgsn1/1s3r1bl/ppp1ppp1p/3p3p1/9/P4P3/1PPPP1PPP/1BK4R1/LNSG1GSNL b - 13"),
    ("descriptor-7", "lnsg2snl/1r2k1gb1/pp1pp1pp1/2p5p/P4p3/L7P/1PPPPPPP1/1BR4S1/1NSGKG1NL b - 13"),
    ("descriptor-8", "1ng1kgsn1/l2s2rbl/ppppppp1p/7p1/3P5/9/PPP1PPPPP/1B1S1R3/LN1GKGSNL b - 13"),
    ("kings", "4k4/9/9/9/9/9/9/9/4K4 b - 1"),
    ("one-pawn", "4k4/9/9/9/9/9/4P4/9/4K4 b - 1"),
    ("one-pawn-white", "4k4/9/9/9/9/9/4P4/9/4K4 w - 1"),
    ("white-pawn", "4k4/9/9/9/9/9/9/4p4/4K4 b - 1"),
)
SHOGI_LOW_BRANCH = frozenset({"kings", "one-pawn", "one-pawn-white", "white-pawn"})


@dataclass(frozen=True)
class Backend:
    game: str
    authority: str
    state: object
    compiled: object | None = None


@dataclass
class SearchStats:
    nodes: int = 0


def _gc_chess_uci(action) -> str:
    text = f"{chr(ord('a') + action.from_square.file)}{action.from_square.rank + 1}"
    text += f"{chr(ord('a') + action.to_square.file)}{action.to_square.rank + 1}"
    if action.promotion_target_id is not None:
        text += action.promotion_target_id.lower()
    return text


def _generic_chess_state(fen: str, compiled) -> GameState:
    from generic_chess.core.identity import position_identity_key

    position = position_from_fen(fen, compiled)
    key = position_identity_key(position, compiled)
    state = GameState(position, 0, ((key, 1),), TerminalResult(TerminalStatus.ONGOING))
    return replace(state, terminal_status=terminal_result(state, compiled))


def _root_backends(game: str, label: str, notation: str):
    if game == "chess":
        compiled = compiled_western_chess()
        return (
            Backend(game, "generic", _generic_chess_state(notation, compiled), compiled),
            Backend(game, "python-chess", chess.Board(notation)),
        )
    compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    return (
        Backend(game, "generic", sfen_to_gc_state(compiled, notation), compiled),
        Backend(game, "cshogi", cshogi.Board(notation)),
    )


def _action_text(backend: Backend, action) -> str:
    if backend.game == "chess":
        return _gc_chess_uci(action) if backend.authority == "generic" else action.uci()
    return gc_action_to_usi(action) if backend.authority == "generic" else cshogi.move_to_usi(action)


def _legal(backend: Backend):
    if backend.authority == "generic":
        actions = legal_actions(backend.state, backend.compiled)
    elif backend.game == "chess":
        actions = list(backend.state.legal_moves)
    else:
        actions = list(backend.state.legal_moves)
    return tuple(sorted(actions, key=lambda action: _action_text(backend, action)))


def _child(backend: Backend, action) -> Backend:
    if backend.authority == "generic":
        return replace(backend, state=apply_action(backend.state, action, backend.compiled))
    board = backend.state.copy(stack=False) if backend.game == "chess" else backend.state.copy()
    board.push(action)
    return replace(backend, state=board)


def _side(backend: Backend) -> int:
    if backend.authority == "generic":
        return backend.state.position.side_to_move
    if backend.game == "chess":
        return 0 if backend.state.turn == chess.WHITE else 1
    return int(backend.state.turn)


def _terminal(backend: Backend) -> tuple[str, int | None]:
    if backend.authority == "generic":
        result = backend.state.terminal_status
        return result.status.value, result.winner
    moves = _legal(backend)
    if moves:
        return "ongoing", None
    if backend.game == "chess":
        check = backend.state.is_check()
    else:
        check = backend.state.is_check()
    return ("checkmate", 1 - _side(backend)) if check else ("stalemate", None)


def _generic_material(backend: Backend) -> int:
    values = CHESS_MATERIAL if backend.game == "chess" else SHOGI_MATERIAL
    position = backend.state.position
    total = 0
    for piece in position.board:
        if piece is not None:
            total += (1 if piece.owner == 0 else -1) * values.get(piece.current_type_id, 0)
    if backend.game == "shogi":
        for owner, hand in enumerate(position.hands):
            sign = 1 if owner == 0 else -1
            for tid, count in hand:
                total += sign * values.get(tid, 0) * count
    return total if _side(backend) == 0 else -total


def _special_material(backend: Backend) -> int:
    if backend.game == "chess":
        total = 0
        for piece in backend.state.piece_map().values():
            total += (1 if piece.color == chess.WHITE else -1) * CHESS_MATERIAL[piece.symbol().upper()]
    else:
        total = 0
        for encoded in backend.state.pieces:
            if not encoded:
                continue
            # cshogi encodes black (side 0) with the low piece ids and
            # white (side 1) with the high ids; the square list is oriented
            # from gote's rank-a side.
            owner = 0 if encoded < 16 else 1
            symbol = cshogi.PIECE_SYMBOLS[encoded & 15].upper()
            total += (1 if owner == 0 else -1) * SHOGI_MATERIAL[symbol]
        for owner, hand in enumerate(backend.state.pieces_in_hand):
            sign = 1 if owner == 0 else -1
            for piece_index, count in enumerate(hand):
                if count:
                    symbol = cshogi.PIECE_SYMBOLS[piece_index + 1].upper()
                    total += sign * SHOGI_MATERIAL[symbol] * count
    return total if _side(backend) == 0 else -total


def _material(backend: Backend) -> int:
    return _generic_material(backend) if backend.authority == "generic" else _special_material(backend)


def _terminal_score(backend: Backend, status: str, winner: int | None, ply: int) -> int:
    if status in {"stalemate", "repetition", "perpetual_check", "max_ply", "no_contest"}:
        return 0
    if status == "checkmate":
        magnitude = MATE_SCORE - ply
        return magnitude if winner == _side(backend) else -magnitude
    return _material(backend)


def _search(backend: Backend, depth: int):
    stats = SearchStats()

    def negamax(node: Backend, remaining: int, alpha: int, beta: int, ply: int):
        stats.nodes += 1
        status, winner = _terminal(node)
        if status != "ongoing":
            return _terminal_score(node, status, winner, ply), ()
        if remaining == 0:
            return _material(node), ()
        best_score = -INF
        best_pv = ()
        for action in _legal(node):
            child = _child(node, action)
            score, pv = negamax(child, remaining - 1, -beta, -alpha, ply + 1)
            score = -score
            text = _action_text(node, action)
            if score > best_score:
                best_score, best_pv = score, (text,) + pv
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        return best_score, best_pv

    started = time.perf_counter()
    score, pv = negamax(backend, depth, -INF, INF, 0)
    elapsed = time.perf_counter() - started
    return {
        "best_move": pv[0] if pv else None,
        "score": score,
        "pv": list(pv),
        "nodes": stats.nodes,
        "wall_seconds": elapsed,
        "nodes_per_second": stats.nodes / elapsed if elapsed else None,
    }


def _production_sanity(game: str, compiled, state):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    player = AlphaBetaPlayer(
        compiled, use_disk_cache=False, use_native_semantic_legality=False,
    )
    decision = player.choose_action(
        session, SearchLimits(max_depth=1, max_nodes=64, quiescence_max_depth=0)
    )
    legal = {str(action) for action in legal_actions(state, compiled)}
    return {
        "selected": None if decision.action is None else str(decision.action),
        "selected_is_legal": decision.action is None or str(decision.action) in legal,
        "termination_reason": decision.termination_reason,
        "nodes": decision.nodes + decision.qnodes,
    }


def _position_row(game: str, label: str, notation: str, low_branch: bool):
    generic, reference = _root_backends(game, label, notation)
    generic_legal = [_action_text(generic, action) for action in _legal(generic)]
    reference_legal = [_action_text(reference, action) for action in _legal(reference)]
    generic_terminal = _terminal(generic)
    reference_terminal = _terminal(reference)
    row = {
        "label": label,
        "notation": notation,
        "low_branch": low_branch,
        "legal_actions": {"generic": generic_legal, "reference": reference_legal},
        "terminal": {"generic": generic_terminal, "reference": reference_terminal},
        "static_material": {"generic": _material(generic), "reference": _material(reference)},
        "search": {},
        "hard_fork": None,
    }
    if generic_legal != reference_legal:
        row["hard_fork"] = "LEGAL_ACTIONS"
        return row
    if generic_terminal != reference_terminal:
        row["hard_fork"] = "TERMINAL"
        return row
    if row["static_material"]["generic"] != row["static_material"]["reference"]:
        row["hard_fork"] = "STATIC_MATERIAL"
        return row
    generic_children = {_action_text(generic, a): _material(_child(generic, a)) for a in _legal(generic)}
    reference_children = {_action_text(reference, a): _material(_child(reference, a)) for a in _legal(reference)}
    if generic_children != reference_children:
        row["child_static_material"] = {"generic": generic_children, "reference": reference_children}
        row["hard_fork"] = "CHILD_STATIC_MATERIAL"
        return row
    depths = [2] + ([3] if low_branch else [])
    for depth in depths:
        left = _search(generic, depth)
        right = _search(reference, depth)
        row["search"][str(depth)] = {"generic": left, "reference": right}
        compared = tuple(left[key] for key in ("best_move", "score", "pv", "nodes"))
        expected = tuple(right[key] for key in ("best_move", "score", "pv", "nodes"))
        if compared != expected:
            row["hard_fork"] = f"SEARCH_DEPTH_{depth}"
            return row
    return row


def run_gate1():
    rows = {"chess": [], "shogi": []}
    first_hard_fork = None
    for game, corpus, low_labels in (
        ("chess", CHESS_POSITIONS, CHESS_LOW_BRANCH),
        ("shogi", SHOGI_POSITIONS, SHOGI_LOW_BRANCH),
    ):
        for label, notation in corpus:
            row = _position_row(game, label, notation, label in low_labels)
            rows[game].append(row)
            if row["hard_fork"] is not None:
                first_hard_fork = {"game": game, "label": label, "reason": row["hard_fork"]}
                break
        if first_hard_fork is not None:
            break
    production = None
    if first_hard_fork is None:
        chess_compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
        chess_state = _generic_chess_state(CHESS_POSITIONS[0][1], chess_compiled)
        shogi_compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
        shogi_state = sfen_to_gc_state(shogi_compiled, SHOGI_POSITIONS[0][1])
        production = {
            "chess": _production_sanity("chess", chess_compiled, chess_state),
            "shogi": _production_sanity("shogi", shogi_compiled, shogi_state),
        }
        if not all(item["selected_is_legal"] for item in production.values()):
            first_hard_fork = {"stage": "production_sanity", "reason": "ILLEGAL_ACTION"}
    return {
        "status": "PASS" if first_hard_fork is None else "FIRST_HARD_FORK",
        "classification": "CAUSAL_DIAGNOSTIC",
        "search": "benchmark-only negamax/alpha-beta; fixed material; canonical action order",
        "corpus_counts": {game: len(items) for game, items in rows.items()},
        "depth_2_counts": {game: sum("2" in row["search"] for row in items) for game, items in rows.items()},
        "depth_3_counts": {game: sum("3" in row["search"] for row in items) for game, items in rows.items()},
        "rows": rows,
        "production_sanity": production,
        "first_hard_fork": first_hard_fork,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_gate1()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
