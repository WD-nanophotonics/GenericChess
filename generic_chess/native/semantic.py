"""Python boundary for the independent Native semantic position state."""

from __future__ import annotations

from . import _module, native_available


def pack_position(native_rules, payload):
    """Pack an independent semantic position.

    ``history`` entries with four 64-bit words are the exact SHA-256
    repetition authority. Two-word entries remain accepted only as an
    explicit legacy transport projection and are not terminal-eligible.
    """
    if not native_available():
        raise RuntimeError("native extension is not built")
    normalized = dict(payload)
    # Keep aux transport explicit and numeric at the C boundary.
    normalized["aux"] = [
        [slot, owner, list(value) if isinstance(value, tuple) else value]
        for (slot, owner), value in payload.get("aux_state", ())
    ]
    if "history" in payload:
        normalized["history"] = [
            [int(word) for word in words] for words in payload["history"]
        ]
    return _module().semantic_pack_position(native_rules.capsule, normalized)


def snapshot(native_rules, position):
    if not native_available():
        raise RuntimeError("native extension is not built")
    out = dict(_module().semantic_position_snapshot(native_rules.capsule, position))
    out["aux_state"] = tuple(
        ((int(entry[0]), int(entry[1])),
         tuple(entry[2]) if isinstance(entry[2], (list, tuple)) else entry[2])
        for entry in out.get("aux_state", ())
    )
    out["history"] = tuple(tuple(int(word) for word in entry) for entry in out.get("history", ()))
    out["history_occurrences"] = int(out.get("history_occurrences", 0))
    return out


def position_key(native_rules, position) -> str:
    """Canonical semantic position identity computed by the Native kernel."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return str(_module().semantic_position_key(native_rules.capsule, position))


def pack_action(fields: dict) -> int:
    """Pack an exact semantic action using the frozen Native bit layout."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_action_pack(dict(fields)))


def unpack_action(action: int) -> dict:
    """Unpack and validate an exact semantic action."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return {key: int(value) for key, value in _module().semantic_action_unpack(int(action)).items()}


def candidate_actions(native_rules, position) -> tuple[int, ...]:
    """Enumerate deterministic S0 geometry candidates (not yet S1-S4 legal)."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(int(action) for action in _module().semantic_candidate_actions(native_rules.capsule, position))


def guarded_actions(native_rules, position) -> tuple[int, ...]:
    """Return exact actions surviving Native S0-S4 checks currently implemented."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return tuple(int(action) for action in _module().semantic_guarded_actions(native_rules.capsule, position))


def history_occurrences(position, lo: int, hi: int) -> int:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_history_occurrences(position, int(lo), int(hi)))


def make_checked(native_rules, position, action: int):
    """Apply an exact semantic candidate in Native and return its child capsule."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _module().semantic_make_checked(native_rules.capsule, position, int(action))


def make_unmake_roundtrip(native_rules, position, action: int) -> dict:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return dict(_module().semantic_make_unmake_roundtrip(native_rules.capsule, position, int(action)))


def candidate_perft(native_rules, position, depth: int) -> int:
    if not native_available():
        raise RuntimeError("native extension is not built")
    return int(_module().semantic_candidate_perft(native_rules.capsule, position, int(depth)))


def probe_search(native_rules, position, depth: int, *, board_values=None, hand_values=None) -> dict:
    """Run the bounded generic AlphaBeta probe over guarded semantic actions.

    This deliberately remains a probe API: it exercises Native checked
    transitions and deterministic PV selection without claiming the final
    semantic search capability gate.
    """
    if not native_available():
        raise RuntimeError("native extension is not built")
    if (board_values is None) != (hand_values is None):
        raise ValueError("board_values and hand_values must be supplied together")
    args = (native_rules.capsule, position, int(depth))
    if board_values is not None:
        args += (tuple(int(value) for value in board_values), tuple(int(value) for value in hand_values))
    raw = dict(_module().semantic_probe_search(*args))
    raw["best_action"] = None if raw.get("best_action") is None else int(raw["best_action"])
    raw["principal_variation"] = tuple(int(value) for value in raw.get("principal_variation", ()))
    raw["score"] = int(raw["score"])
    raw["nodes"] = int(raw["nodes"])
    return raw
