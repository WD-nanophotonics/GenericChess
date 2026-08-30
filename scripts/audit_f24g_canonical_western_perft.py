"""F24G benchmark-provenance correction and canonical Western perft audit."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from generic_chess.core.position import Position
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.serialization import serialize_ruleset

from scripts.audit_f24f_western_chess_perft import (
    compiled_western_chess,
    perft,
    position_from_fen,
    root_divide,
    standard_engine,
)


CANONICAL_CORPUS = (
    ("initial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", (20, 400, 8902, 197281)),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", (48, 2039, 97862)),
    ("position-3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", (14, 191, 2812, 43238)),
    ("position-4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", (6, 264, 9467)),
    ("position-5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", (44, 1486, 62379)),
    ("position-6", "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", (46, 2079, 89890)),
)

F24F_FENS = {
    "kiwipete": "r3k2r/p1ppqpb1/bn2pnp1/2pP4/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1",
    "position-4": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P1PPP/R2Q1RK1 w kq - 0 1",
    "position-6": "r4rk1/1pp1qppp/p1np1n2/2b1p3/2B1P1b1/P1NP1N2/1PP1QPPP/R1B2RK1 w - - 0 10",
}


def canonical_manifest():
    return [
        {"label": label, "fen": fen, "expected": list(expected)}
        for label, fen, expected in CANONICAL_CORPUS
    ]


def canonical_manifest_json():
    return json.dumps(canonical_manifest(), sort_keys=True, separators=(",", ":"))


def canonical_manifest_sha256():
    return hashlib.sha256(canonical_manifest_json().encode()).hexdigest()


def f24f_artifact_sha256(root: Path):
    paths = (
        root / "scripts/audit_f24f_western_chess_perft.py",
        root / "tests/test_f24f_western_chess_perft.py",
        root / "tests/fixtures/f24f_western_chess_perft.json",
        root / "docs/architecture/ADR-082-western-chess-perft-certification.md",
    )
    return {
        str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def loader_sanity(compiled):
    rows = []
    for label, fen, _expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, compiled)
        counts = {}
        for piece in position.board:
            if piece is not None:
                key = f"{piece.owner}:{piece.base_type_id}:{piece.current_type_id}:{int(piece.promoted)}"
                counts[key] = counts.get(key, 0) + 1
        rows.append({
            "label": label,
            "side": position.side_to_move,
            "piece_counts": dict(sorted(counts.items())),
            "castling_aux": list(position.aux_state),
            "aux_sha256": hashlib.sha256(repr(position.aux_state).encode()).hexdigest(),
        })
    return rows


def progressive_canonical_perft():
    compiled, engine = standard_engine()
    results = []
    for label, fen, expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, compiled)
        for depth, wanted in enumerate(expected, 1):
            started = time.perf_counter()
            actual = perft(engine, position, depth)
            elapsed = time.perf_counter() - started
            row = {
                "label": label, "depth": depth, "expected": wanted,
                "actual": actual, "wall_seconds": elapsed,
                "nodes_per_second": actual / elapsed if elapsed else None,
            }
            results.append(row)
            if actual != wanted:
                divide = root_divide(engine, position, depth - 1)
                payload = json.dumps(sorted(divide), separators=(",", ":"))
                return {
                    "status": "FIRST_CANONICAL_MISMATCH",
                    "results": results,
                    "first_mismatch": row,
                    "divide": sorted(divide),
                    "divide_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                }
    return {"status": "PASS", "results": results, "first_mismatch": None}


__all__ = [
    "CANONICAL_CORPUS", "F24F_FENS", "canonical_manifest", "canonical_manifest_json",
    "canonical_manifest_sha256", "compiled_western_chess", "f24f_artifact_sha256",
    "loader_sanity", "position_from_fen", "progressive_canonical_perft", "root_divide",
    "serialize_ruleset", "standard_engine",
]
