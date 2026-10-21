import json
import random
import statistics
import time
from pathlib import Path

from generic_chess import build_western_chess_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.session import GameSession


ROOT_SEEDS = (101, 102, 103)
BUDGETS = (0.005, 0.010, 0.020)
REPEATS = 4
compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
roots = []
for seed in ROOT_SEEDS:
    rng = random.Random(seed)
    session = GameSession(compiled)
    for _ in range(12):
        actions = sorted(session.legal_actions(), key=str)
        if session.result.status.value != "ongoing" or not actions:
            raise RuntimeError("unexpected early terminal")
        session.submit(actions[rng.randrange(len(actions))])
    roots.append((seed, session))

rows = []
for seed, session in roots:
    player = AlphaBetaPlayer(compiled, use_disk_cache=False)
    initial = (session.state, session._search_witnesses)
    for budget in BUDGETS:
        for repeat in range(REPEATS):
            player.reset()
            started = time.perf_counter()
            decision = player.choose_action(
                session,
                SearchLimits(
                    max_depth=8,
                    max_nodes=None,
                    max_time_seconds=budget,
                    quiescence_max_depth=0,
                ),
            )
            external_wall = time.perf_counter() - started
            rows.append(
                {
                    "seed": seed,
                    "budget_seconds": budget,
                    "repeat": repeat,
                    "external_wall_seconds": external_wall,
                    "reported_elapsed_seconds": decision.elapsed_seconds,
                    "first_legal_seconds": decision.time_to_first_legal_action,
                    "first_iteration_seconds": decision.time_to_first_completed_iteration,
                    "nodes": decision.nodes,
                    "qnodes": decision.qnodes,
                    "completed_depth": decision.completed_depth,
                    "reason": decision.termination_reason,
                    "result_source": decision.result_source,
                    "state_unchanged": (session.state, session._search_witnesses) == initial,
                }
            )

summary = []
for budget in BUDGETS:
    group = [row for row in rows if row["budget_seconds"] == budget]
    gaps = [abs(row["reported_elapsed_seconds"] - row["external_wall_seconds"]) for row in group]
    walls = sorted(row["external_wall_seconds"] for row in group)
    summary.append(
        {
            "budget_seconds": budget,
            "n": len(group),
            "external_wall_median": statistics.median(walls),
            "external_wall_p95_nearest_rank": walls[max(0, int(0.95 * len(walls)) - 1)],
            "reported_elapsed_median": statistics.median(row["reported_elapsed_seconds"] for row in group),
            "median_abs_reported_external_gap": statistics.median(gaps),
            "max_overshoot_seconds": max(max(0.0, row["external_wall_seconds"] - budget) for row in group),
            "depth_counts": {
                str(depth): sum(row["completed_depth"] == depth for row in group)
                for depth in sorted({row["completed_depth"] for row in group})
            },
            "median_nodes": statistics.median(row["nodes"] + row["qnodes"] for row in group),
        }
    )

result = {
    "question": "After switching production deadline and elapsed telemetry to perf_counter, do short AlphaBeta caller budgets and reported elapsed values track a high-resolution external timer?",
    "scope": "Three fixed 12-ply seeded standard-chess roots, four repeats each at 5/10/20ms; no training; same search limits and unchanged input state check. This is a timer calibration, not strength evidence.",
    "clock": {
        "implementation": time.get_clock_info("perf_counter").implementation,
        "resolution_seconds": time.get_clock_info("perf_counter").resolution,
        "monotonic": time.get_clock_info("perf_counter").monotonic,
    },
    "rows": rows,
    "summary": summary,
    "all_states_unchanged": all(row["state_unchanged"] for row in rows),
}
output = Path(".local_agent/timed_budget_clock_postfix_20261021.json")
output.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "file": str(output),
            "bytes": output.stat().st_size,
            "clock": result["clock"],
            "summary": summary,
            "all_states_unchanged": result["all_states_unchanged"],
        },
        indent=2,
    )
)
