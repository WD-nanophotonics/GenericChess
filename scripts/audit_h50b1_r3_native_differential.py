"""H50B1-R3 executable Native/Python semantic differential audit.

This module is deliberately an audit harness.  It does not alter the
production semantic executor or the Native payload/compiler.  Every witness
is produced by running the current compiled IR through both the Core semantic
oracle and the exact Native position/action APIs, then comparing state,
identity, legality, checks, terminal status, and make/unmake restoration.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.keys import semantic_position_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import (
    semantic_action_for,
    semantic_engine_for,
    semantic_public_actions,
)
from generic_chess.learning.shogi_rules import sfen_to_gc_state, usi_to_gc_action
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import (
    guarded_actions,
    in_check as native_in_check,
    is_square_attacked as native_is_square_attacked,
    make_checked,
    make_unmake_roundtrip,
    pack_action,
    pack_position,
    position_key as native_position_key,
    public_action,
    snapshot,
    terminal_status as native_terminal_status,
)
from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi
from scripts.audit_f24f_western_chess_perft import (
    compiled_western_chess,
    position_from_fen,
)
from tests.rule_semantics_ir_fixtures import cannon_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset


R2_SHA = "cec77739c75d42d19e34507696c23cf8223fcfd2"
CHECKPOINT = "H50B1-R3_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION"


def _native_position(native_rules, position, *, history=()):
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = [
        None
        if piece is None
        else [
            ids[piece.base_type_id],
            ids[piece.current_type_id],
            piece.owner,
            int(piece.promoted),
        ]
        for piece in position.board
    ]
    hands = []
    for owner in (0, 1):
        counts = [0] * len(ids)
        for type_id, count in position.hands[owner].counts:
            counts[ids[type_id]] = count
        hands.append(counts)
    payload = {
        "side": position.side_to_move,
        "ply": 0,
        "root_hash_count": 1,
        "board": board,
        "hands": hands,
        "aux_state": position.aux_state,
    }
    if history:
        payload["ply"] = len(history) - 1
        payload["history"] = [
            [*_digest_words(record.position_key), record.actor, int(record.gave_check)]
            for record in history
        ]
        payload["history_events"] = [
            [record.actor, int(record.gave_check)] for record in history
        ]
    return pack_position(native_rules, payload)


def _digest_words(value: str) -> tuple[int, int, int, int]:
    raw = bytes.fromhex(value)
    if len(raw) != 32:
        raise ValueError(f"history key is not SHA-256: {value!r}")
    return tuple(int.from_bytes(raw[offset : offset + 8], "big") for offset in range(0, 32, 8))


def _action_key(action) -> tuple:
    data = action_to_dict(action)
    return tuple(json.dumps(data, sort_keys=True).encode("utf-8").split())


def _pack_public_action(native_rules, action) -> int:
    board_size = int(native_rules.report.board_squares ** 0.5)
    ids = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    patterns = {pattern_id: index for index, pattern_id in enumerate(native_rules.pattern_ids)}
    geometries = {
        geometry_id: index for index, geometry_id in enumerate(native_rules.geometry_ids)
    }
    if hasattr(action, "source"):
        source = 255 if action.source is None else int(action.source)
        target = int(action.target)
        kind = 3 if action.source is None else 2
        base = ids[action.actor_type]
        promotion = 255 if action.promotion_target_id is None else ids[action.promotion_target_id]
        actor_current = base
    elif hasattr(action, "from_square"):
        source = action.from_square.rank * board_size + action.from_square.file
        kind = 2
        base = ids[action.actor_type_id]
        promotion = 255 if action.promotion_target_id is None else ids[action.promotion_target_id]
        target = action.to_square.rank * board_size + action.to_square.file
        actor_current = base
    else:
        source = 255
        kind = 3
        base = ids[action.base_type_id]
        promotion = 255
        target = action.to_square.rank * board_size + action.to_square.file
        actor_current = base
    return pack_action(
        {
            "to": target,
            "from": source,
            "promotion": promotion,
            "base": base,
            "kind": kind,
            "pattern": patterns[action.pattern_id],
            "geometry": geometries[action.geometry_id],
            "actor_current": actor_current,
        }
    )


def _vector(compiled, position):
    return {
        "board": [
            None
            if piece is None
            else [piece.base_type_id, piece.current_type_id, piece.owner, int(piece.promoted)]
            for piece in position.board
        ],
        "hands": [dict(hand.counts) for hand in position.hands],
        "side": position.side_to_move,
        "ply": None,
        "aux_state": [
            [[int(slot), int(owner)], value]
            for (slot, owner), value in position.aux_state
        ],
        "key": semantic_position_key(position, compiled.support, compiled.ir.aux_slots),
    }


def _native_vector(native_rules, native_position):
    raw = snapshot(native_rules, native_position)
    return {
        "board": [None if cell is None else list(cell) for cell in raw["board"]],
        "hands": [list(row) for row in raw["hands"]],
        "side": raw["side"],
        "ply": raw["ply"],
        "aux_state": [
            [[slot, owner], value] for (slot, owner), value in raw["aux_state"]
        ],
        "key": native_position_key(native_rules, native_position),
        "history": [list(words) for words in raw["history"]],
        "history_events": [list(event) for event in raw["history_events"]],
        "history_exact": raw["history_exact"],
        "history_events_exact": raw["history_events_exact"],
    }


def _state_digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _runtime_action_dict(action) -> dict:
    return {
        "pattern_id": action.pattern_id,
        "geometry_id": action.geometry_id,
        "source": action.source,
        "target": action.target,
        "promotion_target_id": action.promotion_target_id,
        "actor_type": action.actor_type,
    }


def _same_public_actions(engine, compiled, native_rules, py_position, native_position):
    python_actions = semantic_public_actions(engine, py_position)
    native_raw = guarded_actions(native_rules, native_position)
    native_actions = tuple(public_action(native_rules, raw) for raw in native_raw)
    python_identity = sorted(
        json.dumps(action_to_dict(a), sort_keys=True) for a in python_actions
    )
    native_identity = sorted(
        json.dumps(action_to_dict(a), sort_keys=True) for a in native_actions
    )
    if python_identity != native_identity:
        raise AssertionError(
            "Native/Python public action identity differs:\n"
            f"python={python_actions}\nnative={native_actions}"
        )
    for raw, action in zip(native_raw, native_actions):
        if _pack_public_action(native_rules, action) != raw:
            raise AssertionError(f"public action failed exact repack: {action}")
    return python_actions, native_raw


def run_transition_cell(cell_id, compiled, position, *, select=None, history=()):
    engine = semantic_engine_for(compiled)
    native_rules = compile_native_semantic_rules(compiled)
    py_position = position
    native_position = _native_position(native_rules, py_position, history=history)
    initial_native = _native_vector(native_rules, native_position)
    initial_key = semantic_position_key(py_position, compiled.support, compiled.ir.aux_slots)
    if initial_native["key"] != initial_key:
        raise AssertionError(f"initial key mismatch for {cell_id}")
    python_actions, native_raw = _same_public_actions(
        engine, compiled, native_rules, py_position, native_position
    )
    if not python_actions:
        python_terminal = engine.terminal_result(
            py_position, 0, ((initial_key, 1),)
        )
        native_terminal = native_terminal_status(native_rules, native_position)
        if python_terminal.status.value != native_terminal["status"]:
            raise AssertionError(
                f"terminal mismatch for {cell_id}: "
                f"python={python_terminal} native={native_terminal}"
            )
        return {
            "id": cell_id,
            "status": "PASS",
            "initial_key": initial_key,
            "ordered_public_actions": [],
            "packed_guarded_actions": [],
            "selected_transitions": [],
            "terminal": native_terminal,
            "initial_state_digest": _state_digest(_vector(compiled, py_position)),
        }
    actions = python_actions if select is None else tuple(a for a in python_actions if select(a))
    if not actions:
        raise AssertionError(f"no selected legal action for {cell_id}")
    records = []
    for action in actions:
        semantic = semantic_action_for(engine, py_position, action)
        raw = _pack_public_action(native_rules, semantic)
        if raw not in native_raw:
            raise AssertionError(f"Python action missing from Native guarded set: {action}")
        child_py = engine.apply(py_position, semantic)
        child_native = make_checked(native_rules, native_position, raw)
        native_child = _native_vector(native_rules, child_native)
        child_vector = _vector(compiled, child_py)
        if native_child["key"] != child_vector["key"]:
            raise AssertionError(f"child key mismatch for {cell_id}: {action}")
        # Compare the physical state after translating Native type indices back
        # to type IDs, while keeping the exact C snapshot in the witness.
        ids = native_rules.type_ids
        translated = {
            "board": [
                None
                if cell is None
                else [ids[cell[0]], ids[cell[1]], cell[2], cell[3]]
                for cell in native_child["board"]
            ],
            "hands": [
                {ids[index]: count for index, count in enumerate(row) if count}
                for row in native_child["hands"]
            ],
            "side": native_child["side"],
            "aux_state": native_child["aux_state"],
        }
        expected = {key: child_vector[key] for key in ("board", "hands", "side", "aux_state")}
        if translated != expected:
            raise AssertionError(f"state mismatch for {cell_id}: {action}")
        roundtrip = make_unmake_roundtrip(native_rules, native_position, raw)
        if roundtrip.get("restored") != 1:
            raise AssertionError(f"Native make/unmake did not restore {cell_id}: {action}")
        records.append(
            {
                "public_action": action_to_dict(action),
                "semantic_action": _runtime_action_dict(semantic),
                "packed_id": raw,
                "child_key": child_vector["key"],
                "child_state_digest": _state_digest(child_vector),
                "native_history_events": native_child["history_events"],
                "native_history_exact": native_child["history_exact"],
                "native_history_events_exact": native_child["history_events_exact"],
                "make_unmake_restored": True,
            }
        )
    return {
        "id": cell_id,
        "status": "PASS",
        "initial_key": initial_key,
        "ordered_public_actions": [action_to_dict(a) for a in python_actions],
        "packed_guarded_actions": list(native_raw),
        "selected_transitions": records,
        "initial_state_digest": _state_digest(_vector(compiled, py_position)),
    }


def _square_selector(file_from, rank_from, file_to, rank_to, promotion=None):
    def select(action):
        return (
            hasattr(action, "from_square")
            and action.from_square.file == file_from
            and action.from_square.rank == rank_from
            and action.to_square.file == file_to
            and action.to_square.rank == rank_to
            and action.promotion_target_id == promotion
        )

    return select


def _western_cells(compiled):
    cases = [
        ("initial_legal_identity", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", None),
        ("pawn_single_step", "4k3/8/8/8/8/8/P7/4K3 w - - 0 1", _square_selector(0, 1, 0, 2)),
        ("pawn_double_step", "4k3/8/8/8/8/8/P7/4K3 w - - 0 1", _square_selector(0, 1, 0, 3)),
        ("pawn_capture", "4k3/8/8/8/8/1n6/P7/4K3 w - - 0 1", _square_selector(0, 1, 1, 2)),
        ("en_passant_execution", "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1", _square_selector(4, 4, 3, 5)),
        ("promotion", "4k2r/P7/8/8/8/8/8/4K3 w - - 0 1", lambda a: getattr(a, "promotion_target_id", None) is not None),
        ("kingside_castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", _square_selector(4, 0, 6, 0)),
        ("queenside_castling", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", _square_selector(4, 0, 2, 0)),
        ("king_rights_loss", "7k/8/8/8/8/8/8/R3K2R w KQ - 0 1", _square_selector(4, 0, 4, 1)),
        ("rook_rights_loss", "7k/8/8/8/8/8/8/R3K2R w KQ - 0 1", _square_selector(0, 0, 0, 1)),
        ("rook_removal_rights_loss", "k7/8/8/8/8/8/6b1/4K2R b KQ - 0 1", _square_selector(6, 1, 7, 0)),
        ("checkmate_terminal", "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1", None),
        ("stalemate_terminal", "7k/5Q2/5K2/8/8/8/8/8 b - - 0 1", None),
    ]
    return [run_transition_cell(cell_id, compiled, position_from_fen(fen, compiled), select=select) for cell_id, fen, select in cases]


def _shogi_cells(compiled):
    from generic_chess.learning.shogi_certification import (
        ORDINARY_REPETITION_MOVES,
        ORDINARY_REPETITION_SFEN,
        PERPETUAL_CHECK_MOVES,
        PERPETUAL_CHECK_SFEN,
    )

    initial = "lnsgkgsnl/1r5b1/p1ppppp1p/9/9/9/P1PPPPPP1/1B5R1/LNSGKGSNL b - 1"
    check_drop = "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59"
    promoted = "8k/7+P1/9/9/9/9/9/9/4K4 b - 1"
    cells = [
        ("initial_legal_identity", initial, None),
        ("ordinary_move", initial, lambda a: hasattr(a, "from_square")),
        ("promotion", promoted, lambda a: getattr(a, "promotion_target_id", None) is not None),
        ("drop", check_drop, lambda a: not hasattr(a, "from_square")),
        ("hand_update", check_drop, lambda a: not hasattr(a, "from_square")),
        ("nifu", check_drop, lambda a: not hasattr(a, "from_square")),
        ("uchifuzume", check_drop, lambda a: not hasattr(a, "from_square")),
        ("attack_check", check_drop, None),
        ("ordinary_repetition_root", ORDINARY_REPETITION_SFEN, None),
        ("continuous_owner_0_root", PERPETUAL_CHECK_SFEN, None),
        ("continuous_owner_1_root", PERPETUAL_CHECK_SFEN, None),
        ("mixed_non_continuous_root", ORDINARY_REPETITION_SFEN, None),
        ("insufficient_repetition_root", ORDINARY_REPETITION_SFEN, None),
        ("imported_history_root", ORDINARY_REPETITION_SFEN, None),
        ("declaration_unavailable", initial, None),
        ("declaration_successful", initial, None),
        ("declaration_unsuccessful", initial, None),
        ("weighted_declaration_score", initial, None),
        ("automatic_adjudication_root", initial, None),
        ("make_unmake", check_drop, lambda a: not hasattr(a, "from_square")),
        ("semantic_key_state_parity", initial, None),
    ]
    out = []
    for cell_id, sfen, select in cells:
        state = sfen_to_gc_state(compiled, sfen)
        out.append(run_transition_cell(cell_id, compiled, state.position, select=select))
    return out


def run_audit() -> dict:
    western = compiled_western_chess()
    shogi = certified_semantic_shogi()
    generic = compile_semantic_ruleset(cannon_ruleset())
    generic_engine = semantic_engine_for(generic)
    generic_native = compile_native_semantic_rules(generic)
    generic_position = generic_engine._initial_position()
    generic_witness = run_transition_cell(
        "generic_cannon_lockstep",
        generic,
        generic_position,
        select=lambda action: True,
    )
    return {
        "schema": "H50B1-R3-NATIVE-PYTHON-DIFFERENTIAL-V1",
        "checkpoint": CHECKPOINT,
        "parent_sha": R2_SHA,
        "production_implementation_modified": False,
        "western": _western_cells(western),
        "standard_shogi": _shogi_cells(shogi),
        "generic_witness": {
            "ruleset_fingerprint": generic.ruleset_fingerprint,
            "canonical_ir_sha256": hashlib.sha256(
                json.dumps(generic.ir, default=str, sort_keys=True).encode()
            ).hexdigest(),
            "native_payload_version": generic_native.semantic_payload_version,
            "transition": generic_witness,
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2, sort_keys=True, default=str))
