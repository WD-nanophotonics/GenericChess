"""Paired bounded probe for repeated declaration-ID resolution at root."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import replace

from generic_chess import build_standard_shogi_ruleset, initial_state
from generic_chess.ai.alphabeta import search as search_module
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.declarations import (
    _assess_compiled_declaration_position,
    _available_declarations_position,
    _declarations,
)
from generic_chess.core.errors import ensure_ruleset_match
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session import GameSession


def _pre_change_assess(position, ply, compiled, declaration_id):
    """Reproduce the former list-comprehension ID lookup and assessment."""
    ensure_ruleset_match(position, compiled)
    matches = [
        declaration
        for declaration in _declarations(compiled)
        if declaration.declaration_id == declaration_id
    ]
    if not matches:
        raise ValueError(f"unknown declaration ID {declaration_id!r}")
    return _assess_compiled_declaration_position(
        position, ply, compiled, matches[0]
    )


def _pre_change_available(position, ply, compiled):
    ensure_ruleset_match(position, compiled)
    return tuple(
        assessment
        for declaration in _declarations(compiled)
        if declaration.owner == position.side_to_move
        for assessment in (
            _pre_change_assess(
                position, ply, compiled, declaration.declaration_id
            ),
        )
        if assessment.outcome != "LOSS"
    )


def _median_ms(function, repeats=7):
    samples = []
    value = None
    for _ in range(repeats):
        started = time.perf_counter()
        value = function()
        samples.append((time.perf_counter() - started) * 1000.0)
    return round(statistics.median(samples), 3), value


def _search_once(compiled, session, bridge):
    original = search_module._available_declarations_position
    search_module._available_declarations_position = bridge
    try:
        player = AlphaBetaPlayer(
            compiled,
            use_disk_cache=False,
            use_native_semantic_legality=False,
        )
        return player.choose_action(
            session,
            SearchLimits(
                max_depth=1,
                max_time_seconds=0.001,
                quiescence_max_depth=0,
            ),
        )
    finally:
        search_module._available_declarations_position = original


def main():
    base = build_standard_shogi_ruleset()
    template = next(item for item in base.declarations if item.owner == 0)
    rows = []
    for count in (256, 1024):
        rules = replace(
            base,
            declarations=tuple(
                replace(template, declaration_id=f"claim_{index}")
                for index in range(count)
            ),
        )
        compiled = compile_ruleset_for_execution(rules)
        assert len(compiled.declarations) == count
        position = initial_state(compiled).position
        session = GameSession(compiled)

        old_median, old_options = _median_ms(
            lambda: _pre_change_available(position, 0, compiled)
        )
        new_median, new_options = _median_ms(
            lambda: _available_declarations_position(position, 0, compiled)
        )
        assert old_options == new_options

        old_search_median, old_decision = _median_ms(
            lambda: _search_once(compiled, session, _pre_change_available)
        )
        new_search_median, new_decision = _median_ms(
            lambda: _search_once(compiled, session, _available_declarations_position)
        )
        old_summary = {
            "termination_reason": old_decision.termination_reason,
            "completed_depth": old_decision.completed_depth,
            "action": None if old_decision.action is None else str(old_decision.action),
        }
        new_summary = {
            "termination_reason": new_decision.termination_reason,
            "completed_depth": new_decision.completed_depth,
            "action": None if new_decision.action is None else str(new_decision.action),
        }
        rows.append(
            {
                "declarations": count,
                "compiled_and_accepted": True,
                "core_before_median_ms": old_median,
                "core_after_median_ms": new_median,
                "core_options_equal": True,
                "search_budget_ms": 1,
                "search_before_median_ms": old_search_median,
                "search_after_median_ms": new_search_median,
                "search_result_equal": old_summary == new_summary,
                "search_before": old_summary,
                "search_after": new_summary,
                "legal_fallback": new_decision.action is not None,
            }
        )
    print(json.dumps({"repeats": 7, "results": rows}, indent=2))


if __name__ == "__main__":
    main()
