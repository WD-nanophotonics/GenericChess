"""Paired deterministic node-budget search probe, excluding wall-time policy."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import replace

from generic_chess import build_standard_shogi_ruleset
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


def _old_bridge(position, ply, compiled):
    ensure_ruleset_match(position, compiled)
    out = []
    for declaration in _declarations(compiled):
        if declaration.owner != position.side_to_move:
            continue
        ensure_ruleset_match(position, compiled)
        matches = [
            candidate
            for candidate in _declarations(compiled)
            if candidate.declaration_id == declaration.declaration_id
        ]
        assessment = _assess_compiled_declaration_position(
            position, ply, compiled, matches[0]
        )
        if assessment.outcome != "LOSS":
            out.append(assessment)
    return tuple(out)


def _run(compiled, session, bridge, node_budget):
    original = search_module._available_declarations_position
    search_module._available_declarations_position = bridge
    try:
        player = AlphaBetaPlayer(
            compiled,
            use_disk_cache=False,
            use_native_semantic_legality=False,
            use_tt=False,
            use_ordering=False,
        )
        started = time.perf_counter()
        decision = player.choose_action(
            session,
            SearchLimits(max_depth=4, max_nodes=node_budget, quiescence_max_depth=0),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    finally:
        search_module._available_declarations_position = original
    return elapsed_ms, decision


def _result(decision):
    return {
        "termination_reason": decision.termination_reason,
        "completed_depth": decision.completed_depth,
        "score": decision.score,
        "action": None if decision.action is None else str(decision.action),
        "nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "declaration_checks": decision.declaration_checks,
    }


base = build_standard_shogi_ruleset()
template = next(item for item in base.declarations if item.owner == 0)
results = []
for count in (2, 32, 1024):
    node_budget = 8 if count == 1024 else 128
    rules = replace(
        base,
        declarations=tuple(
            replace(template, declaration_id=f"claim_{index}")
            for index in range(count)
        ),
    )
    compiled = compile_ruleset_for_execution(rules)
    rows = []
    for _ in range(5):
        session = GameSession(compiled)
        old_ms, old = _run(compiled, session, _old_bridge, node_budget)
        new_ms, new = _run(
            compiled, session, _available_declarations_position, node_budget
        )
        old_result, new_result = _result(old), _result(new)
        rows.append(
            {
                "old_ms": round(old_ms, 3),
                "new_ms": round(new_ms, 3),
                "results_equal": old_result == new_result,
                "old": old_result,
                "new": new_result,
                "legal_action": (
                    new.action in session.legal_actions()
                    if new.action is not None
                    else False
                ),
            }
        )
    results.append(
        {
            "declarations": count,
            "compiled_and_accepted": len(compiled.declarations) == count,
            "node_budget": node_budget,
            "runs": rows,
            "old_median_ms": round(statistics.median(row["old_ms"] for row in rows), 3),
            "new_median_ms": round(statistics.median(row["new_ms"] for row in rows), 3),
            "all_results_equal": all(row["results_equal"] for row in rows),
        }
    )

print(json.dumps({"repeats": 5, "results": results}, indent=2))
