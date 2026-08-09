"""Python boundary for the independent Native semantic position state."""

from __future__ import annotations

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
    if "history" in payload:
        normalized["history"] = [
            [int(words[0]), int(words[1])] for words in payload["history"]
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
    out["history"] = tuple(
        (int(entry[0]), int(entry[1])) for entry in out.get("history", ())
    )
    out["history_occurrences"] = int(out.get("history_occurrences", 0))
    return out


def position_key(native_rules, position) -> str:
    """Canonical semantic position identity computed by the Native kernel."""
    if not native_available():
        raise RuntimeError("native extension is not built")
    return str(_module().semantic_position_key(native_rules.capsule, position))
