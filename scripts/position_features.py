"""Offline sparse Position features for semantic evaluation feasibility.

This is a separate research input, not the live compact-model schema. It retains
current/base board identity, promotion flags, hands, side and compiled auxiliary
slots on square or rectangular boards. It does NOT encode GameState history,
provide rule-independent weights, or implement incremental NNUE updates.
"""

from __future__ import annotations

import numpy as np

from generic_chess.core.position import Position
from generic_chess.rules.ir import CompiledSemanticRuleset


class SparsePositionEncoder:
    """Compile one RuleSet's fixed layout; recompute active features per Position.

    Order: current board, base hand, side, three supplied dynamic scalars, aux,
    base board, promoted board. Auxiliary squares use width/height separately.
    Rule fingerprint and type ordering bind the input to this compiled RuleSet;
    equal dimension alone does not permit sharing weights between rules.
    """

    def __init__(self, compiled: CompiledSemanticRuleset):
        if not isinstance(compiled, CompiledSemanticRuleset):
            raise TypeError("sparse Position encoding requires compiled semantic rules")
        self.fingerprint = compiled.ruleset_fingerprint
        self.shape = compiled.board_shape
        self.types = tuple(sorted(compiled.support.type_metadata))
        self.type_index = {type_id: index for index, type_id in enumerate(self.types)}
        self.board_width = len(self.types) * self.shape.area
        self.hand_offset = 2 * self.board_width
        self.side_offset = self.hand_offset + 2 * len(self.types)
        self.dynamic_offset = self.side_offset + 2
        offset = self.dynamic_offset + 3
        slots = []
        for slot in compiled.ir.aux_slots:
            for owner in ((-1,) if slot.scope == "global" else (0, 1)):
                slots.append((offset, (slot.slot_id, owner), slot.value_kind, slot.initial))
                offset += 1 if slot.value_kind == "bool" else 3
        self.aux_slots = tuple(slots)
        self.base_offset = offset
        self.promoted_offset = self.base_offset + 2 * self.board_width
        self.dimension = self.promoted_offset + 2 * self.shape.area

    def encode(self, position: Position, dynamic_values=(0.0, 0.0, 0.0)):
        """Return unique active indices and float64 values; zero terms are omitted.

        Dynamic scalars are supplied measurements, not silently computed zero
        replacements for an evaluator. Callers choosing zero must label that
        ablation. Unknown types fail rather than dropping consequential identity.
        """
        if position.ruleset_fingerprint != self.fingerprint or position.board_shape != self.shape:
            raise ValueError("Position does not belong to this compiled feature layout")
        dynamic = tuple(dynamic_values)
        if len(dynamic) != 3:
            raise ValueError("this research layout has exactly three dynamic scalar axes")
        indices, values = [], []

        def put(index, value):
            if value != 0:
                indices.append(index)
                values.append(float(value))

        area, nt = self.shape.area, len(self.types)
        for square, piece in enumerate(position.board):
            if piece is None:
                continue
            put((piece.owner * nt + self.type_index[piece.current_type_id]) * area + square, 1)
            put(self.base_offset + (piece.owner * nt + self.type_index[piece.base_type_id]) * area + square, 1)
            put(self.promoted_offset + piece.owner * area + square, int(piece.promoted))
        for owner, hand in enumerate(position.hands):
            for type_id, count in hand.counts:
                put(self.hand_offset + owner * nt + self.type_index[type_id], count)
        put(self.side_offset + position.side_to_move, 1)
        for index, value in enumerate(dynamic):
            put(self.dynamic_offset + index, value)
        aux = dict(position.aux_state)
        for offset, key, kind, initial in self.aux_slots:
            value = aux[key] if key in aux else initial
            if kind == "bool":
                put(offset, value or 0)
            elif value is not None:
                put(offset, 1)
                put(offset + 1, value[0] / self.shape.width)
                put(offset + 2, value[1] / self.shape.height)
        return np.asarray(indices, dtype=np.intp), np.asarray(values, dtype=np.float64)

    def dense(self, position: Position, dynamic_values=(0.0, 0.0, 0.0)) -> np.ndarray:
        """Materialize the research layout for inspection; search need not do so."""
        indices, values = self.encode(position, dynamic_values)
        result = np.zeros(self.dimension, dtype=np.float64)
        result[indices] = values
        return result
