"""Python <-> native position/action adapters (root-boundary only)."""

from __future__ import annotations

from typing import Any

from ..core.actions import BoardMove, DropMove, action_from_dict, action_to_dict
from ..core.keys import position_key
from ..rules.compiled import CompiledRuleSet
from .compiler import NativeCompiledRules, native_available

_NO_SQUARE = 0xFF


def pack_native_position(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    state,
):
    """Pack a Python GameState into a native position capsule (one-time cost)."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    if compiled.ruleset_fingerprint != native_rules.fingerprint:
        raise ValueError("ruleset fingerprint mismatch while packing position")
    n = compiled.board_size
    board = []
    for piece in state.position.board:
        if piece is None:
            board.append(None)
        else:
            board.append(
                [
                    native_rules.type_map[piece.base_type_id],
                    native_rules.type_map[piece.current_type_id],
                    piece.owner,
                    1 if piece.promoted else 0,
                ]
            )
    hands = []
    for owner in (0, 1):
        counts = [0] * native_rules.type_count
        for tid, count in state.position.hands[owner].counts:
            counts[native_rules.type_map[tid]] = count
        hands.append(counts)
    current_key = position_key(state.position, compiled)
    root_count = dict(state.repetition_counts).get(current_key, 1)
    payload = {
        "side": state.position.side_to_move,
        "ply": state.ply_count,
        "root_hash_count": root_count,
        "board": board,
        "hands": hands,
    }
    from . import _module

    return _module().pack_position(native_rules.capsule, payload)


def decode_action(native_rules: NativeCompiledRules, packed: int) -> dict:
    """Decode a packed native action into a plain dict (square indices)."""
    to = packed & 0xFF
    frm = (packed >> 8) & 0xFF
    promo = (packed >> 16) & 0xFF
    base = (packed >> 24) & 0xFF
    kind = (packed >> 32) & 0xF
    if kind == 1:
        return {
            "kind": "drop",
            "base_type_id": native_rules.type_ids[base],
            "to_square": to,
        }
    return {
        "kind": "board",
        "from_square": frm,
        "to_square": to,
        "promotion_target_id": (
            native_rules.type_ids[promo] if promo != _NO_SQUARE else None
        ),
        "base_type_id": native_rules.type_ids[base],
    }


def to_python_action(native_rules: NativeCompiledRules, packed: int):
    """Decode a packed native action into a Core Action (absolute coords)."""
    from ..core.coordinates import Square

    n = native_rules.report.board_squares ** 0.5
    n = int(n)

    def square(idx: int) -> Square:
        return Square(idx % n, idx // n)

    decoded = decode_action(native_rules, packed)
    if decoded["kind"] == "drop":
        return DropMove(decoded["base_type_id"], square(decoded["to_square"]))
    return BoardMove(
        square(decoded["from_square"]),
        square(decoded["to_square"]),
        decoded["promotion_target_id"],
    )


def native_legal_actions(native_rules: NativeCompiledRules, position_capsule) -> tuple:
    from . import _module

    return tuple(
        _module().native_legal_actions(native_rules.capsule, position_capsule)
    )


def native_terminal(native_rules: NativeCompiledRules, position_capsule) -> str:
    from . import _module

    return str(_module().native_terminal(native_rules.capsule, position_capsule))


def native_snapshot(native_rules: NativeCompiledRules, position_capsule) -> dict:
    from . import _module

    return dict(_module().native_snapshot(native_rules.capsule, position_capsule))


def native_child_snapshot(
    native_rules: NativeCompiledRules, position_capsule, packed: int
) -> dict:
    from . import _module

    return dict(
        _module().native_child_snapshot(
            native_rules.capsule, position_capsule, packed
        )
    )


def native_perft(
    native_rules: NativeCompiledRules,
    position_capsule,
    depth: int,
    *,
    divide: bool = False,
) -> dict:
    from . import _module

    result = dict(
        _module().native_perft(
            native_rules.capsule, position_capsule, depth, divide
        )
    )
    if "divide" in result:
        result["divide"] = dict(result["divide"])
    return result


def native_make_unmake_roundtrip(
    native_rules: NativeCompiledRules, position_capsule, packed: int
) -> dict:
    from . import _module

    return dict(
        _module().native_make_unmake_roundtrip(
            native_rules.capsule, position_capsule, packed
        )
    )


def snapshot_to_python(native_rules: NativeCompiledRules, snapshot: dict) -> dict:
    """Convert a native snapshot dict into type-id-keyed Python semantics."""
    n = int(native_rules.report.board_squares ** 0.5)
    board = []
    for cell in snapshot["board"]:
        if cell is None:
            board.append(None)
        else:
            base, current, owner, promoted = cell
            board.append(
                {
                    "base_type_id": native_rules.type_ids[base],
                    "current_type_id": native_rules.type_ids[current],
                    "owner": owner,
                    "promoted": bool(promoted),
                }
            )
    hands = []
    for owner_counts in snapshot["hands"]:
        hands.append(
            {
                native_rules.type_ids[i]: count
                for i, count in enumerate(owner_counts)
                if count
            }
        )
    return {
        "side_to_move": snapshot["side_to_move"],
        "ply": snapshot["ply"],
        "board": board,
        "hands": hands,
        "terminal": snapshot["terminal"],
        "repetition_count": snapshot["repetition_count"],
        "hash_lo": snapshot["hash_lo"],
        "hash_hi": snapshot["hash_hi"],
    }
