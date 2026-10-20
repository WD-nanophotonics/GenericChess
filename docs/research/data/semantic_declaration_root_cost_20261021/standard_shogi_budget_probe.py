"""Seven normal Standard Shogi AlphaBeta calls at a cooperative 20 ms budget."""

from __future__ import annotations

import json
import statistics
import time

from generic_chess import build_standard_shogi_ruleset
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session import GameSession


compiled = compile_ruleset_for_execution(build_standard_shogi_ruleset())
runs = []
for _ in range(7):
    session = GameSession(compiled)
    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        use_native_semantic_legality=False,
    )
    started = time.perf_counter()
    decision = player.choose_action(
        session,
        SearchLimits(
            max_depth=4,
            max_time_seconds=0.020,
            quiescence_max_depth=0,
        ),
    )
    runs.append(
        {
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "termination_reason": decision.termination_reason,
            "completed_depth": decision.completed_depth,
            "nodes": decision.nodes,
            "declaration_checks": decision.declaration_checks,
            "action": None if decision.action is None else str(decision.action),
            "legal_action": (
                decision.action in session.legal_actions()
                if decision.action is not None
                else False
            ),
        }
    )

print(
    json.dumps(
        {
            "compiled_declarations": len(compiled.declarations),
            "budget_ms": 20,
            "runs": runs,
            "median_elapsed_ms": round(
                statistics.median(row["elapsed_ms"] for row in runs), 3
            ),
        },
        indent=2,
    )
)
