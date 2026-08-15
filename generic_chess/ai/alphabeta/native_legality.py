"""Production Native semantic legal-action provider.

The provider is intentionally owned by the AI layer.  Core sees only the
callable contract ``(position, ply_count, checkpoint) -> pairs`` and remains
Native-unaware.  The provider performs one state-only pack, one transient
Native legality call, direct packed-action decoding, and exact Python binding
reconstruction without invoking the Python S0-S4 generator.
"""

from __future__ import annotations

import time
import threading

from ...core.coordinates import index_to_square
from ...core.semantic_executor import (
    SemanticAction,
    _semantic_public_action,
    semantic_engine_for,
)
from ...rules.ir import CompiledSemanticRuleset


_U8 = 0xFF
_GEOMETRY_MASK = 0xFFF
_MAX_U64 = (1 << 64) - 1


class NativeSemanticLegalityProvider:
    """Callable, compile-once Native semantic legality route."""

    def __init__(self, compiled, engine, native_rules, *, strict: bool = False):
        self.compiled = compiled
        self.engine = engine
        self.native_rules = native_rules
        self.strict = bool(strict)
        self.type_ids = tuple(native_rules.type_ids)
        self.type_map = {type_id: index for index, type_id in enumerate(self.type_ids)}
        self.pattern_ids = tuple(native_rules.pattern_ids)
        self.geometry_ids = tuple(native_rules.geometry_ids)
        self.pattern_by_id = {pattern.pattern_id: pattern for pattern in engine._patterns}
        self._metrics_local = threading.local()
        self.compile_seconds = 0.0

    @property
    def last_call_metrics(self):
        return getattr(self._metrics_local, "last", {})

    @classmethod
    def try_create(cls, compiled, *, strict: bool = False):
        """Create an active provider or return ``None`` for normal fallback."""
        if not isinstance(compiled, CompiledSemanticRuleset):
            return None
        engine = semantic_engine_for(compiled)
        if engine is None:
            return None
        started = time.perf_counter()
        try:
            # Deferred imports avoid a package-initialization cycle when the
            # compiler is imported directly by Native contract tests.
            from ...native.compiler import compile_native_semantic_rules

            native_rules = compile_native_semantic_rules(compiled)
            if not native_rules.native_executable:
                return None
        except Exception:
            return None
        provider = cls(compiled, engine, native_rules, strict=strict)
        provider.compile_seconds = time.perf_counter() - started
        return provider

    def _state_only_payload(self, position, ply_count):
        """Build exactly the F20 state-only payload; never read history/SHA."""
        board = []
        for piece in position.board:
            if piece is None:
                board.append(None)
                continue
            if piece.owner not in (0, 1):
                raise ValueError("Native legality payload has an invalid owner")
            try:
                base = self.type_map[piece.base_type_id]
                current = self.type_map[piece.current_type_id]
            except KeyError as exc:
                raise ValueError("Native legality payload has an unknown piece type") from exc
            board.append([base, current, int(piece.owner), int(bool(piece.promoted))])

        hands = []
        for hand in position.hands:
            counts = [0] * len(self.type_ids)
            for type_id, count in hand.counts:
                if type_id not in self.type_map:
                    raise ValueError("Native legality payload has an unknown hand type")
                if int(count) < 0:
                    raise ValueError("Native legality payload has a negative hand count")
                counts[self.type_map[type_id]] = int(count)
            hands.append(counts)
        return {
            "side": int(position.side_to_move),
            "ply": int(ply_count),
            "board": board,
            "hands": hands,
            "aux_state": tuple(position.aux_state),
        }

    def _decode_action(self, packed: int, position):
        """Decode the frozen 64-bit layout without one FFI call per action."""
        if not isinstance(packed, int) or isinstance(packed, bool) or not 0 <= packed <= _MAX_U64:
            raise ValueError("Native legality returned a non-u64 action")
        to = packed & _U8
        source = (packed >> 8) & _U8
        promotion = (packed >> 16) & _U8
        base_index = (packed >> 24) & _U8
        kind = (packed >> 32) & 0xF
        pattern_index = (packed >> 36) & _U8
        geometry_index = (packed >> 44) & _GEOMETRY_MASK
        actor_index = (packed >> 56) & _U8
        board_squares = self.compiled.board_size * self.compiled.board_size
        if to >= board_squares:
            raise ValueError("Native legality returned an out-of-range target")
        if kind not in (2, 3):
            raise ValueError("Native legality returned a non-semantic action")
        if pattern_index >= len(self.pattern_ids) or geometry_index >= len(self.geometry_ids):
            raise ValueError("Native legality returned an out-of-range rule index")
        if actor_index >= len(self.type_ids) or base_index >= len(self.type_ids):
            raise ValueError("Native legality returned an out-of-range type index")
        if kind == 3:
            if source != _U8 or promotion != _U8 or actor_index != base_index:
                raise ValueError("Native legality returned an invalid drop encoding")
            source_value = None
        else:
            if source >= board_squares:
                raise ValueError("Native legality returned an out-of-range source")
            piece = position.board[source]
            if piece is None or piece.owner != position.side_to_move:
                raise ValueError("Native legality returned a source without the side-to-move piece")
            if self.type_map[piece.base_type_id] != base_index:
                raise ValueError("Native legality returned a mismatched base type")
            if self.type_map[piece.current_type_id] != actor_index:
                raise ValueError("Native legality returned a mismatched actor type")
            source_value = source
        pattern_id = self.pattern_ids[pattern_index]
        geometry_id = self.geometry_ids[geometry_index]
        actor_type = self.type_ids[actor_index]
        promotion_type = None if promotion == _U8 else self.type_ids[promotion] if promotion < len(self.type_ids) else None
        if promotion != _U8 and promotion_type is None:
            raise ValueError("Native legality returned an out-of-range promotion type")
        return SemanticAction(
            pattern_id=pattern_id,
            source=source_value,
            target=to,
            promotion_target_id=promotion_type,
            actor_type=actor_type,
            geometry_id=geometry_id,
        )

    def __call__(self, position, ply_count, checkpoint=None):
        from ...native.semantic import pack_position, transient_legal_actions

        started = time.perf_counter()
        if checkpoint is not None:
            checkpoint()
        payload_started = time.perf_counter()
        payload = self._state_only_payload(position, ply_count)
        native_position = pack_position(self.native_rules, payload)
        payload_seconds = time.perf_counter() - payload_started
        if checkpoint is not None:
            checkpoint()
        raw_actions = transient_legal_actions(self.native_rules, native_position)
        if checkpoint is not None:
            checkpoint()

        decoded_started = time.perf_counter()
        pairs = []
        for index, packed in enumerate(raw_actions):
            if index and index % 64 == 0 and checkpoint is not None:
                checkpoint()
            semantic_action = self._decode_action(int(packed), position)
            pattern = self.pattern_by_id.get(semantic_action.pattern_id)
            if pattern is None:
                raise ValueError("Native legality returned an unknown pattern")
            binding = self.engine._make_binding_from_action(
                position, semantic_action, pattern
            )
            public = _semantic_public_action(self.engine, semantic_action)
            pairs.append((public, (semantic_action, binding)))
        if checkpoint is not None:
            checkpoint()
        self._metrics_local.last = {
            "payload_seconds": payload_seconds,
            "decode_binding_seconds": time.perf_counter() - decoded_started,
            "total_seconds": time.perf_counter() - started,
            "actions": len(pairs),
        }
        return tuple(pairs)


__all__ = ["NativeSemanticLegalityProvider"]
