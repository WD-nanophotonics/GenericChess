"""Python <-> native position/action adapters (root-boundary only)."""

from __future__ import annotations

from typing import Any

from ..core.actions import BoardMove, DropMove, action_from_dict, action_to_dict
from ..core.coordinates import Square, square_to_index
from ..core.identity import repetition_identity_key
from ..core.identity import position_identity_key
from ..core.transition import apply_action, initial_state
from ..rules.compiled import CompiledRuleSet
from .compiler import (
    GC_MAX_HAND,
    NativeActionError,
    NativeCompiledRules,
    native_available,
)

_NO_SQUARE = 0xFF


def _build_payload(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    state,
    *,
    root_hash_count: int,
) -> dict:
    """Shared payload builder with hand-count capacity validation."""
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
            if count > GC_MAX_HAND:
                raise ValueError(
                    f"hand count {count} for {tid!r} exceeds native limit "
                    f"{GC_MAX_HAND} (fingerprint {compiled.ruleset_fingerprint})"
                )
            counts[native_rules.type_map[tid]] = count
        hands.append(counts)
    return {
        "side": state.position.side_to_move,
        "ply": state.ply_count,
        "root_hash_count": root_hash_count,
        "board": board,
        "hands": hands,
    }


def pack_native_position(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    state,
):
    """Pack a Python GameState into a native position capsule (one-time cost).

    The legacy perft-oriented entry: history starts at the packed root and the
    Python root repetition count is folded in via ``root_hash_count``.
    """
    current_key = repetition_identity_key(state.position, compiled)
    root_count = dict(state.repetition_counts).get(current_key, 1)
    payload = _build_payload(
        compiled, native_rules, state, root_hash_count=root_count
    )
    from . import _module

    return _module().pack_position(native_rules.capsule, payload)


def pack_action(
    native_rules: NativeCompiledRules,
    action,
    *,
    base_type_id: str,
) -> int:
    """Pack a Core Action into the native 64-bit layout (root boundary)."""
    n = int(native_rules.report.board_squares**0.5)
    if isinstance(action, DropMove):
        to = action.to_square.rank * n + action.to_square.file
        base = native_rules.type_map[action.base_type_id]
        return (
            (to & 0xFF)
            | (0xFF << 8)
            | (0xFF << 16)
            | ((base & 0xFF) << 24)
            | (1 << 32)
        )
    from_i = action.from_square.rank * n + action.from_square.file
    to_i = action.to_square.rank * n + action.to_square.file
    promo = (
        native_rules.type_map[action.promotion_target_id]
        if action.promotion_target_id is not None
        else 0xFF
    )
    base = native_rules.type_map[base_type_id]
    return (
        (to_i & 0xFF)
        | ((from_i & 0xFF) << 8)
        | ((promo & 0xFF) << 16)
        | ((base & 0xFF) << 24)
    )


def pack_native_search_position(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    session,
):
    """Pack a search root by replaying the full session history natively.

    The initial state is packed (``root_hash_count=0``), then every recorded
    action is replayed through the *checked* native make path so the native
    history stack contains the complete game path.  This is a root-boundary
    one-time cost, never part of the search hot path.
    """
    state = initial_state(compiled)
    payload = _build_payload(
        compiled, native_rules, state, root_hash_count=0
    )
    packed_actions = session_packed_actions(compiled, native_rules, session)
    from . import _module

    pos = _module().replay_position(
        native_rules.capsule, payload, tuple(packed_actions)
    )
    _verify_replay_root(compiled, native_rules, pos, session)
    return pos


def pack_semantic_search_position(compiled, native_rules, session):
    """Pack an exact :class:`GameSession` root for semantic Native search.

    Unlike the legacy adapter, this transport preserves the complete semantic
    position-key history and the actor/check event stream.  The initial
    sentinel is explicit so repetition and continuous-check adjudication stay
    authoritative inside Native.
    """
    if compiled.ruleset_fingerprint != native_rules.fingerprint:
        raise ValueError("ruleset fingerprint mismatch while packing semantic position")
    state = session.state
    n = compiled.board_size
    type_map = {type_id: index for index, type_id in enumerate(native_rules.type_ids)}
    board = []
    for piece in state.position.board:
        board.append(None if piece is None else [
            type_map[piece.base_type_id], type_map[piece.current_type_id],
            int(piece.owner), int(piece.promoted),
        ])
    hands = []
    for owner in (0, 1):
        counts = [0] * len(native_rules.type_ids)
        for type_id, count in state.position.hands[owner].counts:
            counts[type_map[type_id]] = int(count)
        hands.append(counts)

    history = []
    records = state.history
    if len(records) != len(session._search_witnesses):
        raise ValueError("semantic session history witness length mismatch")
    for witness, record in zip(session._search_witnesses, records):
        key = str(position_identity_key(witness, compiled))
        if len(key) != 64:
            raise ValueError("semantic position identity must be a SHA-256 hex key")
        words = tuple(int(key[offset:offset + 16], 16) for offset in range(0, 64, 16))
        history.append(words + (255 if record.actor < 0 else int(record.actor), int(bool(record.gave_check))))

    payload = {
        "side": int(state.position.side_to_move),
        "ply": int(state.ply_count),
        "board": board,
        "hands": hands,
        "history": history,
        "aux_state": tuple(state.position.aux_state),
    }
    from .semantic import pack_position, position_key

    native_position = pack_position(native_rules, payload)
    if position_key(native_rules, native_position) != str(position_identity_key(state.position, compiled)):
        raise ValueError("semantic Native root key does not match GameSession state")
    return native_position


def session_packed_actions(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    session,
) -> list[int]:
    """Pack every recorded action in order, tracking the Python side state so
    board moves carry the mover's base type."""
    state = initial_state(compiled)
    n = compiled.board_size
    packed_actions = []
    for record in session.history:
        action = record.action
        if isinstance(action, BoardMove):
            piece = state.position.board[
                square_to_index(action.from_square, n)
            ]
            if piece is None:
                raise ValueError(
                    f"history replay: no mover at {action.from_square} "
                    f"(ply {record.ply}, fingerprint {compiled.ruleset_fingerprint})"
                )
            base_type_id = piece.base_type_id
        else:
            base_type_id = action.base_type_id
        packed_actions.append(
            pack_action(native_rules, action, base_type_id=base_type_id)
        )
        state = apply_action(state, action, compiled)
    return packed_actions


def _verify_replay_root(compiled, native_rules, pos, session) -> None:
    """Compare the replayed native root against the Python session state."""
    snapshot = native_snapshot(native_rules, pos)
    py = snapshot_to_python(native_rules, snapshot)
    state = session.state
    n = compiled.board_size
    if py["side_to_move"] != state.position.side_to_move:
        raise ValueError(
            f"replay root side mismatch (fingerprint {compiled.ruleset_fingerprint})"
        )
    if py["ply"] != state.ply_count:
        raise ValueError(
            f"replay root ply mismatch: native {py['ply']} vs python "
            f"{state.ply_count} (fingerprint {compiled.ruleset_fingerprint})"
        )
    py_board = py["board"]
    for idx, piece in enumerate(state.position.board):
        py_cell = py_board[idx]
        if piece is None:
            if py_cell is not None:
                raise ValueError(
                    f"replay root board mismatch at {idx}: expected empty, "
                    f"native has {py_cell}"
                )
            continue
        if py_cell is None or (
            py_cell["base_type_id"] != piece.base_type_id
            or py_cell["current_type_id"] != piece.current_type_id
            or py_cell["owner"] != piece.owner
            or py_cell["promoted"] != piece.promoted
        ):
            raise ValueError(
                f"replay root board mismatch at {idx} "
                f"(fingerprint {compiled.ruleset_fingerprint})"
            )
    for owner in (0, 1):
        py_hand = py["hands"][owner]
        py_hand = {tid: c for tid, c in py_hand.items() if c}
        if py_hand != dict(state.position.hands[owner].counts):
            raise ValueError(
                f"replay root hand mismatch for owner {owner} "
                f"(fingerprint {compiled.ruleset_fingerprint})"
            )
    if py["terminal"] != state.terminal_status.status.value:
        raise ValueError(
            f"replay root terminal mismatch: native {py['terminal']} vs "
            f"python {state.terminal_status.status.value} "
            f"(fingerprint {compiled.ruleset_fingerprint})"
        )


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


def native_long_make_unmake_roundtrip(
    compiled: CompiledRuleSet,
    native_rules: NativeCompiledRules,
    session,
) -> dict:
    """Replay the full session history natively, then unmake everything and
    verify the position/hash/history return to the packed initial state."""
    from ..core.transition import initial_state
    from . import _module

    state = initial_state(compiled)
    payload = _build_payload(
        compiled, native_rules, state, root_hash_count=0
    )
    actions = session_packed_actions(compiled, native_rules, session)
    return dict(
        _module().native_long_make_unmake_roundtrip(
            native_rules.capsule, payload, tuple(actions)
        )
    )


def native_make_checked(
    native_rules: NativeCompiledRules, position_capsule, packed: int
) -> dict:
    """Public checked make: returns the child snapshot or raises
    :class:`NativeActionError` with structured failure context."""
    from . import _module

    try:
        return dict(
            _module().native_make_checked(
                native_rules.capsule, position_capsule, packed
            )
        )
    except _module().NativeActionError as exc:
        fields = dict(exc.args[0]) if exc.args else {}
        raise NativeActionError(
            "native checked make rejected action "
            f"0x{fields.get('packed', 0):016X}: {fields.get('reason', 'unknown')}",
            fields,
        ) from exc


def native_fixed_depth_search(
    native_rules: NativeCompiledRules,
    eval_capsule,
    position_capsule,
    depth: int,
) -> dict:
    from . import _module

    result = dict(
        _module().native_fixed_depth_search(
            native_rules.capsule, eval_capsule, position_capsule, depth
        )
    )
    result["principal_variation"] = tuple(result["principal_variation"])
    return result


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
