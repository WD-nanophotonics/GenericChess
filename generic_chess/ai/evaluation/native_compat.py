"""Native-compatible material evaluator.

This evaluator mirrors the C ``gc_evaluate_material`` kernel exactly: board
current-type material plus hand base-type material, in the side-to-move
perspective, with anchors carrying no material value.  It deliberately does
not reproduce the dynamic terms of the production :class:`Evaluator`
(mobility, anchor escape, promotion potential), so differential search tests
compare Python and native with identical semantics.
"""

from __future__ import annotations

from ...rules.compiled import CompiledRuleSet
from .config import MAX_STATIC_EVAL
from .profile import RuleSetEvaluationProfile


def evaluate_native_reference(state, compiled: CompiledRuleSet, profile: RuleSetEvaluationProfile) -> int:
    """Material-only score in the side-to-move perspective, clamped to
    ``[-MAX_STATIC_EVAL, MAX_STATIC_EVAL]``."""
    score = 0
    for piece in state.position.board:
        if piece is None:
            continue
        value = profile.board_value_by_type[piece.current_type_id]
        score += value if piece.owner == 0 else -value
    for owner in (0, 1):
        for type_id, count in state.position.hands[owner].counts:
            value = profile.hand_value_by_base_type[type_id]
            score += count * value if owner == 0 else -count * value
    if state.position.side_to_move == 1:
        score = -score
    return max(-MAX_STATIC_EVAL, min(MAX_STATIC_EVAL, score))


class NativeCompatibleEvaluator:
    """Callable adapter with the same ``evaluate(state)`` surface as the
    production evaluator but the native-compatible material formula only."""

    def __init__(
        self,
        compiled: CompiledRuleSet,
        profile: RuleSetEvaluationProfile,
        config,
    ) -> None:
        self._compiled = compiled
        self._profile = profile
        self._config = config

    def evaluate(self, state) -> int:
        return evaluate_native_reference(state, self._compiled, self._profile)

    def type_value(self, type_id: str) -> int:
        return self._profile.board_value_by_type[type_id]
