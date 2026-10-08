"""Opt-in semantic attack authority for the existing dynamic score terms.

Does not change static prices, weights, promotion or anchor-escape geometry.
Attack coverage is not legal mobility. Native imports the current state on each
evaluation; no persistent shadow, hidden fallback or cross-position cache.
"""
from __future__ import annotations

from ...core.coordinates import index_to_square
from ...core.semantic_executor import semantic_engine_for
from .evaluator import Evaluator


class SemanticAttackEvaluator(Evaluator):
    """Use with AlphaBetaPlayer(evaluator_override=...), explicitly opt-in.

    ``backend='core'`` is portable authority; ``'native'`` requires supported
    executable Native rules. Attacks do not require history. Failure is
    surfaced to the caller rather than silently changing score semantics.
    """

    def __init__(self, compiled, profile, config, *, backend="core"):
        super().__init__(compiled, profile, config)
        if backend not in ("core", "native"):
            raise ValueError("semantic attack backend must be core or native")
        self._attack_backend = backend
        self._attack_engine = semantic_engine_for(compiled)
        if self._attack_engine is None:
            raise ValueError("semantic attack evaluator requires compiled semantic rules")
        self._attack_native_rules = None
        if backend == "native":
            from ...native.compiler import compile_native_semantic_rules
            self._attack_native_rules = compile_native_semantic_rules(compiled)

    def _attack_maps(self, state):
        if self._attack_backend == "native":
            from ...native.semantic import attacked_squares, pack_current_position
            position = pack_current_position(
                self._attack_native_rules, state.position, ply_count=state.ply_count)
            maps = tuple(attacked_squares(self._attack_native_rules, position, owner)
                         for owner in (0, 1))
        else:
            maps = tuple(self._attack_engine.attacked_squares(state.position, owner)
                         for owner in (0, 1))
        return tuple(frozenset(index_to_square(i, state.position.board_shape) for i in indices)
                     for indices in maps)
