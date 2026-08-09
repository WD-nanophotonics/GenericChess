"""Python boundary for the independent Native semantic position state."""

from __future__ import annotations

from . import _module, native_available


def pack_position(native_rules, payload):
    if not native_available():
        raise RuntimeError("native extension is not built")
    return _module().semantic_pack_position(native_rules.capsule, payload)


def snapshot(native_rules, position):
    if not native_available():
        raise RuntimeError("native extension is not built")
    return dict(_module().semantic_position_snapshot(native_rules.capsule, position))
