"""Bounded Chess material-change counterfactual with exact short-mate labels."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.native.compiler import compile_native_semantic_rules
from scripts.audit_chess_mate2_qsearch import (
    _certificate,
    _key,
    _later_mate_certificate,
    _python_search,
)
from scripts.f156_known_game_shallow_search_equivalence import (
    _native_run,
    _values,
    _western_pair,
    _western_state,
)


FEN = "8/8/8/pR6/8/8/5R2/k2K4 w - - 0 1"


def run_probe() -> dict:
    compiled, semantic = _western_pair()
    state = _western_state(compiled, FEN)
    labels, certificate = _certificate(compiled, state)
    values = _values(compiled)
    py_q0 = _python_search(compiled, state, values, 2, 0)
    py_q4 = _python_search(compiled, state, values, 2, 4)
    successors = {_key(action): (action, child) for action, child in legal_successors(state, compiled)}
    q0_key = json.dumps(py_q0["action"], sort_keys=True)
    q4_key = json.dumps(py_q4["action"], sort_keys=True)
    q0_action, q0_child = successors[q0_key]
    later = _later_mate_certificate(compiled, q0_child)

    native = compile_native_semantic_rules(semantic)
    native_state = _western_state(semantic, FEN)
    native_q0 = _native_run(semantic, native, native_state, values, 2)
    pawn_before = sum(
        piece is not None and piece.owner == 1 and piece.current_type_id == "P"
        for piece in state.position.board
    )
    pawn_after = sum(
        piece is not None and piece.owner == 1 and piece.current_type_id == "P"
        for piece in q0_child.position.board
    )
    valid = (
        certificate["label_counts"] == {"FORCED_MATE_IN_TWO": 3, "UNRESOLVED": 30}
        and labels[q0_key] == "UNRESOLVED"
        and labels[q4_key] == "FORCED_MATE_IN_TWO"
        and "capture" in q0_action.pattern_id
        and (pawn_before, pawn_after) == (1, 0)
        and not later["forced_mate_within_three_plies_from_root"]
        and later["forced_mate_within_five_plies_from_root"]
        and py_q0["completed_depth"] == py_q4["completed_depth"] == 2
        and native_q0["action"] == py_q0["action"]
    )
    return {
        "classification": "MATERIAL_CHANGE_BOTH_WIN_PASS" if valid else "OBSERVATION_CHANGED",
        "root_fen": FEN,
        "certificate": certificate,
        "python_d2_q0": {**py_q0, "short_label": labels[q0_key]},
        "python_d2_q4": {**py_q4, "short_label": labels[q4_key]},
        "native_d2_q0": native_q0,
        "black_pawns_before_after_q0": [pawn_before, pawn_after],
        "q0_later_certificate": later,
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["classification"] == "MATERIAL_CHANGE_BOTH_WIN_PASS" else 1)
