"""Persistent AlphaSho JSONL worker for the Round 5 positive-control benchmark.

The worker is intentionally outside the AlphaSho repository.  It imports the
read-only checkout and keeps one player instance per profile alive for the
whole benchmark, so process startup is not charged to move timings.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import asdict
from pathlib import Path

ROOT = Path(os.environ.get("GC_ALPHASHO_ROOT", r"C:\Users\icywo\PycharmProjects\alphasho"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import cshogi  # noqa: E402
from alphasho.domain import (  # noqa: E402
    Color,
    GameOutcome,
    GameSnapshot,
    MoveOption,
    OutcomeReason,
    PieceType,
    ThinkingConfig,
    ThinkingPreset,
    ThinkingStrategy,
)
from alphasho.heuristicplayer import HeuristicPlayer  # noqa: E402
from benchmarks.legacy_3262cc8 import LegacyHeuristicPlayer  # noqa: E402


_HAND_PIECES = (PieceType.PAWN, PieceType.LANCE, PieceType.KNIGHT,
                PieceType.SILVER, PieceType.GOLD, PieceType.BISHOP,
                PieceType.ROOK)


def _move_option(usi: str) -> MoveOption:
    if len(usi) == 4 and usi[1] == "*":
        piece = {"P": PieceType.PAWN, "L": PieceType.LANCE,
                 "N": PieceType.KNIGHT, "S": PieceType.SILVER,
                 "G": PieceType.GOLD, "B": PieceType.BISHOP,
                 "R": PieceType.ROOK}[usi[0]]
        to = (int(usi[2]) - 1) * 9 + (ord(usi[3]) - ord("a"))
        return MoveOption(usi, to_square=to, drop_piece=piece)
    to = (int(usi[2]) - 1) * 9 + (ord(usi[3]) - ord("a"))
    source = (int(usi[0]) - 1) * 9 + (ord(usi[1]) - ord("a"))
    return MoveOption(usi, to_square=to, from_square=source, promotion=usi.endswith("+"))


def _snapshot(sfen: str, initial_sfen: str, history: list[str]) -> tuple[GameSnapshot, list[MoveOption]]:
    board = cshogi.Board(initial_sfen or sfen)
    for usi in history:
        board.push_usi(usi)
    if board.sfen().split()[:3] != sfen.split()[:3]:
        raise ValueError("snapshot replay mismatch")
    legal = [_move_option(cshogi.move_to_usi(int(move))) for move in board.legal_moves
             if cshogi.move_cap(move) != 8]
    cells = []
    for raw in board.pieces:
        piece = int(raw)
        if not piece:
            cells.append(None)
        else:
            color = Color.WHITE if piece >= 16 else Color.BLACK
            cells.append((color, piece - 16 if piece >= 16 else piece))
    hands = tuple(tuple(int(x) for x in board.pieces_in_hand[color]) for color in (0, 1))
    snapshot = GameSnapshot(
        board=tuple(cells),
        hands=hands,
        turn=Color.BLACK if board.turn == cshogi.BLACK else Color.WHITE,
        move_number=int(board.move_number),
        is_check=bool(board.is_check()),
        last_move=None,
        move_history=tuple(history),
        sfen=sfen,
        outcome=GameOutcome(OutcomeReason.ONGOING),
        initial_sfen=initial_sfen,
    )
    return snapshot, legal


def _thinking(request: dict) -> ThinkingConfig:
    if request["budget_kind"] == "nodes":
        return ThinkingConfig(
            strategy=ThinkingStrategy.FIXED_PLAYOUT,
            preset=ThinkingPreset.CUSTOM,
            max_playouts=int(request["budget"]),
            max_depth=128,
            safety_margin_ms=0,
        )
    return ThinkingConfig(
        strategy=ThinkingStrategy.FIXED_TIME,
        preset=ThinkingPreset.CUSTOM,
        move_time_seconds=float(request["budget"]),
        max_playouts=10_000_000,
        max_depth=128,
        safety_margin_ms=0,
    )


players: dict[tuple[str, str], object] = {}


def _player(profile: str, request: dict):
    key = (profile, request["budget_kind"])
    if key not in players:
        thinking = _thinking(request)
        players[key] = (
            LegacyHeuristicPlayer(thinking)
            if profile == "legacy"
            else HeuristicPlayer(thinking)
        )
    return players[key]


def _evaluate(sfen: str) -> int:
    from benchmarks.legacy_3262cc8 import LegacyHeuristicPlayer

    return int(LegacyHeuristicPlayer._evaluate(cshogi.Board(sfen)))


def main() -> int:
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request = json.loads(raw)
        try:
            command = request.get("command")
            if command == "ping":
                response = {"ok": True, "command": "ping", "alphasho_root": str(ROOT)}
            elif command == "evaluate_legacy":
                response = {"ok": True, "score": _evaluate(request["sfen"])}
            elif command == "choose":
                snapshot, legal = _snapshot(
                    request["sfen"], request.get("initial_sfen", ""), request.get("history", [])
                )
                if not legal:
                    raise ValueError("no legal moves")
                player = _player(request["profile"], request)
                # The public desktop choose_move() intentionally means an
                # untimed move.  Round 5 needs an exact per-move wall budget,
                # so the benchmark adapter invokes the same frozen search
                # implementation with its explicit deadline.
                if request["budget_kind"] == "seconds":
                    chosen = player._search(  # benchmark-only adapter
                        snapshot, legal, float(request["budget"]),
                        10_000_000, 128, None,
                    )
                else:
                    chosen = player._search(  # benchmark-only adapter
                        snapshot, legal, None, int(request["budget"]), 128, None,
                    )
                info = getattr(player, "last_search_info", None)
                response = {
                    "ok": True,
                    "bestmove": chosen.usi,
                    "search_info": asdict(info) if info is not None else None,
                }
            elif command == "shutdown":
                print(json.dumps({"ok": True, "command": "shutdown"}), flush=True)
                return 0
            else:
                raise ValueError(f"unknown command: {command!r}")
        except Exception as exc:  # protocol errors are explicit evidence
            response = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=8),
            }
        print(json.dumps(response, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
