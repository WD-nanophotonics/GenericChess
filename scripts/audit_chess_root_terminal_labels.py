"""Certify immediate Chess root outcomes by Python/native legal transitions."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    guarded_actions,
    make_checked,
    pack_position,
    public_action,
    terminal_status,
)
from scripts.audit_f24f_western_chess_perft import position_from_fen
from scripts.f156_known_game_shallow_search_equivalence import _western_pair, _western_state


FEN = "8/8/8/1R6/8/8/5R2/k1K5 w - - 0 1"


def _key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True)


def native_position_from_fen(semantic_rules, native, fen):
    position = position_from_fen(fen, semantic_rules)
    ids = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = [
        None if piece is None else [
            ids[piece.base_type_id],
            ids[piece.current_type_id],
            piece.owner,
            int(piece.promoted),
        ]
        for piece in position.board
    ]
    return pack_position(
        native,
        {
            "side": position.side_to_move,
            "ply": 0,
            "board": board,
            "hands": [[0] * len(ids), [0] * len(ids)],
            "aux_state": position.aux_state,
        },
    )


def run_probe() -> dict:
    if not native_available():
        return {"classification": "NATIVE_UNAVAILABLE", "root_fen": FEN}

    python_rules, semantic_rules = _western_pair()
    state = _western_state(python_rules, FEN)
    python_rows = {}
    for action in legal_actions(state, python_rules):
        result = apply_action(state, action, python_rules).terminal_status
        python_rows[_key(action)] = (result.status.value, result.winner)

    native = compile_native_semantic_rules(semantic_rules)
    packed = native_position_from_fen(semantic_rules, native, FEN)
    native_rows = {}
    for action in guarded_actions(native, packed):
        result = terminal_status(native, make_checked(native, packed, action))
        native_rows[_key(public_action(native, action))] = (
            result["status"], result["winner"]
        )

    matches = python_rows == native_rows
    counts = Counter(status for status, _winner in python_rows.values())
    immediate_wins = [
        json.loads(action)
        for action, result in python_rows.items()
        if result == ("checkmate", 0)
    ]
    return {
        "classification": "TERMINAL_LABEL_PARITY_PASS" if matches else "TERMINAL_LABEL_MISMATCH",
        "root_fen": FEN,
        "root_status": state.terminal_status.status.value,
        "python_legal_actions": len(python_rows),
        "native_legal_actions": len(native_rows),
        "terminal_counts": dict(sorted(counts.items())),
        "immediate_wins": sorted(immediate_wins, key=lambda row: (row["from"], row["to"])),
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["classification"] == "TERMINAL_LABEL_PARITY_PASS" else 1)
