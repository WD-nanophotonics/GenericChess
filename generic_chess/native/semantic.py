"""Python boundary for the independent Native semantic position state."""

from __future__ import annotations

import hashlib
import json

from . import _module, native_available


def pack_position(native_rules, payload):
    if not native_available():
        raise RuntimeError("native extension is not built")
    normalized = dict(payload)
    # Keep aux transport explicit and numeric at the C boundary.
    normalized["aux"] = [
        [slot, owner, list(value) if isinstance(value, tuple) else value]
        for (slot, owner), value in payload.get("aux_state", ())
    ]
    return _module().semantic_pack_position(native_rules.capsule, normalized)


def snapshot(native_rules, position):
    if not native_available():
        raise RuntimeError("native extension is not built")
    return dict(_module().semantic_position_snapshot(native_rules.capsule, position))


def position_key(native_rules, position) -> str:
    """Canonical semantic position identity at the Python/native boundary.

    The byte contract intentionally mirrors ``core.keys.semantic_position_key``;
    native state never relies on platform struct layout or Python hash().
    """
    snap = snapshot(native_rules, position)
    board = []
    for cell in snap["board"]:
        if cell is None:
            board.append(None)
        else:
            base, current, owner, promoted = cell
            board.append([owner, native_rules.type_ids[base], native_rules.type_ids[current], bool(promoted)])
    hands = [[
        [[native_rules.type_ids[i], count] for i, count in enumerate(snap["hands"][owner]) if count]
        for owner in (0, 1)
    ]]
    payload = {
        "ruleset": native_rules.fingerprint,
        "side_to_move": snap["side"],
        "board": board,
        "hands": hands,
        "aux_state": {},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
