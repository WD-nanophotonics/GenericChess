import json, statistics, time, random
from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, "tests")
from rule_semantics_ir_fixtures import cannon_ruleset
from generic_chess import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits

rules = cannon_ruleset()
n = rules.board_size
rows = [[None for _ in range(n)] for _ in range(n)]
rows[0][0] = Piece(0, "K", "K")
rows[n-1][n-1] = Piece(1, "K", "K")
for owner, square in ((0,(2,2)), (0,(3,5)), (1,(5,3)), (1,(6,6))):
    rows[square[0]][square[1]] = Piece(owner, "C", "C")
rules = replace(rules, initial_position=tuple(tuple(row) for row in rows))
compiled = compile_ruleset_for_execution(rules)

roots = []
for seed in (17, 29, 43):
    session = GameSession(compiled)
    for ply in range(4):
        actions = sorted(session.legal_actions(), key=str)
        if session.result.status.value != "ongoing" or not actions:
            raise RuntimeError(f"unexpected terminal root path seed={seed} ply={ply}")
        session.submit(actions[(seed + ply * 7) % len(actions)])
    roots.append((seed, session))

qpc = time.perf_counter
coarse = time.monotonic
rows_out = []
for seed, session in roots:
    player = AlphaBetaPlayer(compiled, use_disk_cache=False)
    before = (session.state, tuple(session._search_witnesses))
    # Warm the evaluator/runtime once, then clear search state before measured calls.
    player.choose_action(session, SearchLimits(max_depth=1, max_nodes=16, quiescence_max_depth=0))
    player.reset()
    legal = set(session.legal_actions())
    for budget in (0.010, 0.020):
        for rep in range(2):
            order = ("coarse", "qpc") if rep % 2 == 0 else ("qpc", "coarse")
            pair = {}
            for arm in order:
                player.reset()
                time.perf_counter = coarse if arm == "coarse" else qpc
                try:
                    t0 = qpc()
                    d = player.choose_action(session, SearchLimits(
                        max_depth=8, max_nodes=None, max_time_seconds=budget,
                        quiescence_max_depth=0))
                    external = qpc() - t0
                finally:
                    time.perf_counter = qpc
                pair[arm] = {
                    "external_seconds": external,
                    "reported_elapsed_seconds": d.elapsed_seconds,
                    "nodes": d.nodes + d.qnodes,
                    "completed_depth": d.completed_depth,
                    "reason": d.termination_reason,
                    "action": str(d.action) if d.action is not None else None,
                    "action_legal": d.action in legal,
                }
            rows_out.append({
                "seed": seed, "budget_seconds": budget, "rep": rep,
                "order": order, "arms": pair,
                "state_and_history_unchanged": (session.state, tuple(session._search_witnesses)) == before,
            })

summary = []
for budget in (0.010, 0.020):
    group = [r for r in rows_out if r["budget_seconds"] == budget]
    for arm in ("coarse", "qpc"):
        summary.append({
            "budget_seconds": budget, "arm": arm, "calls": len(group),
            "external_median": statistics.median(r["arms"][arm]["external_seconds"] for r in group),
            "reported_median": statistics.median(r["arms"][arm]["reported_elapsed_seconds"] for r in group),
            "median_nodes": statistics.median(r["arms"][arm]["nodes"] for r in group),
            "depths": {str(d): sum(r["arms"][arm]["completed_depth"] == d for r in group)
                       for d in sorted({r["arms"][arm]["completed_depth"] for r in group})},
            "all_actions_legal": all(r["arms"][arm]["action_legal"] for r in group),
        })
result = {
    "question": "Does the measured Windows coarse-clock deadline distortion also appear on a generated semantic ruleset with legal history preserved?",
    "scope": "One 8x8 semantic cannon ruleset, four explicitly placed cannon pieces, three deterministic legal 4-ply roots, paired coarse GetTickCount64-counterfactual versus QPC calls at 10/20ms, two alternating repeats per root/cap. Evaluator warmed once. No training or strength claim.",
    "clock_sources": {
        "coarse": {"implementation": time.get_clock_info("monotonic").implementation,
                   "resolution": time.get_clock_info("monotonic").resolution},
        "qpc": {"implementation": time.get_clock_info("perf_counter").implementation,
                "resolution": time.get_clock_info("perf_counter").resolution},
    },
    "rows": rows_out,
    "summary": summary,
    "all_states_and_histories_unchanged": all(r["state_and_history_unchanged"] for r in rows_out),
    "all_actions_legal": all(r["arms"][arm]["action_legal"] for r in rows_out for arm in ("coarse", "qpc")),
}
out = Path(".local_agent/timed_budget_semantic_clock_20261021.json")
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"file": str(out), "bytes": out.stat().st_size,
                  "clock_sources": result["clock_sources"], "summary": summary,
                  "all_states_and_histories_unchanged": result["all_states_and_histories_unchanged"],
                  "all_actions_legal": result["all_actions_legal"]}, indent=2))
