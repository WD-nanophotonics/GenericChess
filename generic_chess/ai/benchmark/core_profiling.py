"""Microbenchmarks of Core hot-path functions on mined fixtures.

These measure the real function boundaries of the existing Core (movegen
parts, legality, attacks, transitions, keys) without adding instrumentation
to Core itself.
"""

from __future__ import annotations

import time
from typing import Callable

from ...core.attacks import is_in_check, pseudo_attacks
from ...core.keys import position_key
from ...core.movegen import (
    _apply_action_unchecked,
    _drop_actions,
    _is_legal,
    _piece_actions,
    _promotion_variants,
    legal_actions_from_position,
)
from ...core.repetition import update_repetition_counts
from ...core.terminal import _terminal_from_parts
from ...core.transition import legal_successors
from .audit_schema import medians_min_max


def _measure(fn: Callable[[], object], repeats: int, warmup: int = 1) -> dict:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - started)
    return medians_min_max(samples)


def core_function_timings(
    compiled,
    state,
    *,
    repeats: int = 5,
    warmup: int = 1,
) -> dict:
    """Per-call timings of the main Core hot-path functions."""
    position = state.position
    side = position.side_to_move
    actions = legal_actions_from_position(position, compiled)
    first = actions[0] if actions else None
    key = position_key(position, compiled)
    n = compiled.board_size

    def pseudo_moves():
        return _piece_actions(position, compiled)

    def drop_moves():
        return _drop_actions(position, compiled)

    def expanded_pseudo():
        count = 0
        for a in _piece_actions(position, compiled):
            if hasattr(a, "promotion_target_id"):
                piece = position.board[a.from_square.rank * n + a.from_square.file]
                count += len(_promotion_variants(a, piece, position, compiled))
            else:
                count += 1
        return count + len(_drop_actions(position, compiled))

    def legality_of_first():
        return _is_legal(position, first, compiled)

    def legal_moves():
        return legal_actions_from_position(position, compiled)

    def successors():
        return legal_successors(state, compiled)

    def check():
        return is_in_check(position, side, compiled)

    def attacks0():
        return pseudo_attacks(position, 0, compiled)

    def attacks1():
        return pseudo_attacks(position, 1, compiled)

    def pkey():
        return position_key(position, compiled)

    def repeat_update():
        return update_repetition_counts(state.repetition_counts, key)

    def terminal():
        return _terminal_from_parts(position, state.ply_count, state.repetition_counts, compiled)

    def mechanical_transition():
        if first is None:
            return None
        return _apply_action_unchecked(position, first, compiled)

    functions = {
        "pseudo_action_generation": pseudo_moves,
        "drop_action_generation": drop_moves,
        "pseudo_action_expansion": expanded_pseudo,
        "legality_filter_per_action": legality_of_first if first is not None else None,
        "move_generation_legal": legal_moves,
        "legal_successors": successors,
        "is_in_check": check,
        "pseudo_attacks_owner0": attacks0,
        "pseudo_attacks_owner1": attacks1,
        "position_key": pkey,
        "repetition_update": repeat_update,
        "terminal_detection": terminal,
        "mechanical_transition": mechanical_transition if first is not None else None,
    }
    timings = {}
    for name, fn in functions.items():
        if fn is None:
            continue
        timings[name] = _measure(fn, repeats=repeats, warmup=warmup)
    return {
        "legal_actions": len(actions),
        "pseudo_actions": expanded_pseudo(),
        "pseudo_legal_ratio": round(expanded_pseudo() / max(1, len(actions)), 3),
        "functions": timings,
    }
