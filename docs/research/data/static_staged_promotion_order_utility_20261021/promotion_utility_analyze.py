from __future__ import annotations

import collections
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "promotion-utility-plan.json").read_text(encoding="utf-8"))
RUN = HERE / "promotion-utility-run"
GAMES = [json.loads(line) for line in (RUN / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
RESULT = json.loads((RUN / "result.json").read_text(encoding="utf-8"))
ROOTS = {row["root_id"]: row for row in json.loads((RUN / "roots.json").read_text(encoding="utf-8"))}

assert RESULT["status"] == "COMPLETE"
assert len(GAMES) == PLAN["physical_games"] == 64
assert RESULT["unstarted_slots"] == RESULT["invalid_actions"] == RESULT["replay_mismatches"] == 0
assert len({g["game_id"] for g in GAMES}) == 64 and len(ROOTS) == 16

by_pair = collections.defaultdict(dict)
for game in GAMES:
    by_pair[(game["root_id"], game["candidate_owner"])][game["variant"]] = game
assert len(by_pair) == 32
assert all(set(arms) == {"unit_promotion_order", "static_promotion_order"} for arms in by_pair.values())


def first_candidate(game):
    return next((move for move in game["moves"] if move["role"] == "candidate"), None)


pairs = []
for (root_id, owner), arms in by_pair.items():
    unit = arms["unit_promotion_order"]
    static = arms["static_promotion_order"]
    assert unit["root_state_sha256"] == static["root_state_sha256"]
    first_u, first_s = first_candidate(unit), first_candidate(static)
    same_state = first_u is not None and first_s is not None and first_u["state_before"] == first_s["state_before"]
    low = (-1 if static["reward"] is None else static["reward"]) - (1 if unit["reward"] is None else unit["reward"])
    high = (1 if static["reward"] is None else static["reward"]) - (-1 if unit["reward"] is None else unit["reward"])
    root = ROOTS[root_id]
    pairs.append({
        "root_id": root_id, "seed": root["seed"], "prefix_plies": root["prefix_plies"],
        "parity": "odd" if root["prefix_plies"] % 2 else "even", "owner": owner,
        "low": low, "high": high,
        "nodes_unit": unit["candidate_nodes"], "nodes_static": static["candidate_nodes"],
        "candidate_seconds_unit": sum(m["elapsed_seconds"] for m in unit["moves"] if m["role"] == "candidate"),
        "candidate_seconds_static": sum(m["elapsed_seconds"] for m in static["moves"] if m["role"] == "candidate"),
        "caller_seconds_unit": unit["caller_seconds"], "caller_seconds_static": static["caller_seconds"],
        "node_reduction": (unit["candidate_nodes"] - static["candidate_nodes"]) / max(unit["candidate_nodes"], 1),
        "unknown_static": static["reward"] is None, "unknown_unit": unit["reward"] is None,
        "first_candidate_state_equal": same_state,
        "first_candidate_action_changed": bool(same_state and first_u["action"] != first_s["action"]),
    })


def summarize(rows):
    if not rows:
        return {"n": 0}
    n = len(rows)
    return {
        "n": n, "utility_lower": sum(r["low"] for r in rows) / n,
        "utility_upper": sum(r["high"] for r in rows) / n,
        "median_candidate_node_reduction": statistics.median(r["node_reduction"] for r in rows),
        "nodes_unit": sum(r["nodes_unit"] for r in rows),
        "nodes_static": sum(r["nodes_static"] for r in rows),
        "candidate_seconds_unit": sum(r["candidate_seconds_unit"] for r in rows),
        "candidate_seconds_static": sum(r["candidate_seconds_static"] for r in rows),
        "caller_seconds_unit": sum(r["caller_seconds_unit"] for r in rows),
        "caller_seconds_static": sum(r["caller_seconds_static"] for r in rows),
        "unknown_pairs": sum(r["unknown_static"] or r["unknown_unit"] for r in rows),
        "first_state_comparable": sum(r["first_candidate_state_equal"] for r in rows),
        "first_action_changes": sum(r["first_candidate_action_changed"] for r in rows),
    }


views = {
    "all": pairs,
    "owner0": [r for r in pairs if r["owner"] == 0],
    "owner1": [r for r in pairs if r["owner"] == 1],
    "odd": [r for r in pairs if r["parity"] == "odd"],
    "even": [r for r in pairs if r["parity"] == "even"],
}
summaries = {name: summarize(rows) for name, rows in views.items()}
loo = [{"omitted_seed": seed, **summarize([r for r in pairs if r["seed"] != seed])}
       for seed in sorted({r["seed"] for r in pairs})]
utility_gate = all(summaries[name]["utility_lower"] > 0 for name in views) and all(r["utility_lower"] > 0 for r in loo)
cost_gate = all(summaries[name]["median_candidate_node_reduction"] >= 0.10 for name in views) and all(
    summaries[name]["utility_lower"] >= 0 for name in views
)
analysis = {
    "schema": "primary-staged-promotion-order-analysis-v1",
    "plan_sha256": hashlib.sha256((HERE / "promotion-utility-plan.json").read_bytes()).hexdigest().upper(),
    "source_head": RESULT["source_head"], "slots": len(GAMES), "terminals": RESULT["actual_terminals"],
    "unknown_slots": RESULT["unknown"], "invalid_actions": RESULT["invalid_actions"],
    "replay_mismatches": RESULT["replay_mismatches"], "unstarted_slots": RESULT["unstarted_slots"],
    "terminal_reasons": dict(collections.Counter(g["terminal_reason"] for g in GAMES)),
    "rewards": {variant: dict(collections.Counter(str(g["reward"]) for g in GAMES if g["variant"] == variant))
                for variant in ("unit_promotion_order", "static_promotion_order")},
    "summary": summaries, "leave_one_seed_out": loo,
    "utility_gate": utility_gate, "cost_gate": cost_gate,
    "retain_scoped_candidate": utility_gate or cost_gate,
    "pairs": pairs,
    "per_seed": [{"seed": seed, **summarize([r for r in pairs if r["seed"] == seed])}
                 for seed in sorted({r["seed"] for r in pairs})],
    "limits": "Finite budget and this generated sample only; staged picker remains opt-in; no default or broad price law.",
}
print(json.dumps({k: v for k, v in analysis.items() if k not in ("pairs", "leave_one_seed_out", "per_seed")}, sort_keys=True))
(RUN / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
