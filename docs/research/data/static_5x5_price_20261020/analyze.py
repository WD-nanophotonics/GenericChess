"""Audit and summarize the frozen 5x5 static-vs-Unit panel without searches."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
sys.path.insert(0, str(ROOT))

from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))


def digest(value) -> str:
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def mean_bounds(rows):
    lows, highs = [], []
    finite = []
    for static_reward, unit_reward in rows:
        s_lo, s_hi = (-1, 1) if static_reward is None else (static_reward, static_reward)
        u_lo, u_hi = (-1, 1) if unit_reward is None else (unit_reward, unit_reward)
        lows.append(s_lo - u_hi)
        highs.append(s_hi - u_lo)
        if static_reward is not None and unit_reward is not None:
            finite.append(static_reward - unit_reward)
    n = len(rows)
    return {
        "pairs": n,
        "finite_pairs": len(finite),
        "unknown_pairs": n - len(finite),
        "finite_mean": None if not finite else sum(finite) / len(finite),
        "all_slot_lower": sum(lows) / n,
        "all_slot_upper": sum(highs) / n,
        "finite_values": finite,
    }


def main():
    plan_bytes = (HERE / "plan.json").read_bytes()
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    assert plan_sha == "0abae0d201d157db231f64c94bf6965be1aee14fb01d87a0df14426be25f52c9"
    rules = {}
    for i, seed in enumerate(PLAN["rules"]["seeds"]):
        cfg = GeneratorConfig(
            seed=seed, board_size=5,
            setup_preset=PLAN["rules"]["setups_by_seed_order"][i % 3],
            movement_symmetry=PLAN["rules"]["movement_symmetry_by_seed_order"][i % 2],
            allow_hybrid=True, require_promotable_type=True,
            require_nonpromotable_type=True, max_generation_attempts=16,
            require_no_opening_win_in_one=False,
        )
        generated = generate_game(cfg)
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        rules[str(seed)] = (generated.ruleset, compiled)

    games = [json.loads(line) for line in (HERE / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    queries = [json.loads(line) for line in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if line]
    planned_ids = {
        f"{seed}-{family}|foe={foe}|candidate={candidate}|owner={owner}"
        for seed in PLAN["rules"]["seeds"] for family in range(2)
        for foe in PLAN["arms"]["fixed_foes"]
        for candidate in PLAN["arms"]["candidates"] for owner in (0, 1)
    }
    assert len(games) == PLAN["arms"]["physical_games"]
    assert len({r["game_id"] for r in games}) == len(games)
    assert {r["game_id"] for r in games} == planned_ids
    assert len(queries) == sum(r["queries"] for r in games)
    query_counts = Counter(q["game_id"] for q in queries)
    assert all(query_counts[r["game_id"]] == r["queries"] for r in games)

    reasons = Counter()
    outcomes = Counter()
    action_kinds = Counter()
    replayed = 0
    for row in games:
        seed, family = row["game_id"].split("|", 1)[0].split("-")
        generated_ruleset, compiled = rules[seed]
        serialized_rule = json.loads((HERE / f"rule-{seed}.json").read_text(encoding="utf-8"))
        assert ruleset_to_dict(generated_ruleset) == serialized_rule
        record = deserialize_game_record(json.dumps(row["final_record"]))
        session = GameSession.replay(compiled, record)
        assert digest(session.state) == row["final_state_sha256"]
        assert session.result.winner == row["winner"]
        executed_events = sum("state_after" in move for move in row["moves"])
        assert (
            len(record.actions) - len(row["opening_actions"])
            + (1 if record.declaration is not None else 0)
            == executed_events
        )
        assert (row["terminal_reason"] == "NO_EXECUTABLE_RETURN_UNKNOWN") == (
            bool(row["moves"]) and "state_after" not in row["moves"][-1]
        )
        replayed += 1
        reasons[row["terminal_reason"]] += 1
        outcomes["UNKNOWN" if row["reward"] is None else str(row["reward"])] += 1
        for move in row["moves"]:
            action = move.get("action")
            if action is not None:
                if "base_type_id" in action:
                    action_kinds["drop"] += 1
                else:
                    assert "actor_type_id" in action
                    action_kinds["board"] += 1
                    if action.get("promotion_target_id") is not None:
                        action_kinds["promotion"] += 1

    lookup = {(g["game_id"].split("|", 1)[0], g["foe"], g["candidate_owner"], g["candidate"]): g for g in games}
    by_foe = {}
    by_seed = {}
    seed_bounds = defaultdict(list)
    for foe in PLAN["arms"]["fixed_foes"]:
        pairs = []
        for root in sorted({g["game_id"].split("|", 1)[0] for g in games}):
            for owner in (0, 1):
                static = lookup[(root, foe, owner, "static_v2")]
                unit = lookup[(root, foe, owner, "unit")]
                assert static["opening_actions"] == unit["opening_actions"]
                assert static["root_state_sha256"] == unit["root_state_sha256"]
                pairs.append((static["reward"], unit["reward"]))
                seed = static["game_id"].split("|", 1)[0].split("-")[0]
                seed_bounds[(foe, seed)].append((static["reward"], unit["reward"]))
        summary = mean_bounds(pairs)
        summary.pop("finite_values")
        by_foe[foe] = summary
    for (foe, seed), rows in sorted(seed_bounds.items()):
        summary = mean_bounds(rows)
        by_seed[f"foe={foe}|seed={seed}"] = {
            k: summary[k] for k in ("pairs", "finite_pairs", "unknown_pairs", "finite_mean", "all_slot_lower", "all_slot_upper")
        }

    result = json.loads((HERE / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "COMPLETE" and result["unstarted_slots"] == 0
    assert result["actual_terminals"] == reasons["ACTUAL_TERMINAL"]
    assert result["unknown"] == sum(v for k, v in outcomes.items() if k == "UNKNOWN")
    analysis = {
        "schema": "primary-static-5x5-price-transfer-analysis-v1",
        "plan_sha256": plan_sha,
        "producer_sha256": hashlib.sha256((HERE / "producer.py").read_bytes()).hexdigest(),
        "planned_slots": len(planned_ids), "returned_slots": len(games),
        "replayed_full_records": replayed, "query_records": len(queries),
        "terminal_reasons": dict(sorted(reasons.items())),
        "candidate_rewards": dict(sorted(outcomes.items())),
        "actual_action_kinds": dict(sorted(action_kinds.items())),
        "planned_horizon_candidate_plies": PLAN["outcomes"]["ongoing_after_96_candidate_plies"],
        "implemented_total_ply_cap": 96,
        "maximum_observed_candidate_plies": max(
            sum(1 for m in g["moves"] if m["side"] == g["candidate_owner"] and "state_after" in m)
            for g in games
        ),
        "protocol_deviation": "Producer stopped after 96 total plies, while plan specified 96 candidate plies. All records are retained and the result only describes the actually implemented shorter horizon; it does not close the registered 96-candidate-ply question.",
        "fixed_foe_static_minus_unit": by_foe,
        "linked_seed_families": by_seed,
        "result_summary": result,
        "interpretation": "Finite paired evidence only for these 8 generated 5x5 rules and fixed budgets; unknown slots retain [-1,1] per candidate outcome. Linked seed rows are descriptive, not population confidence.",
    }
    body = json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (HERE / "analysis.json").write_text(body, encoding="utf-8")
    print(json.dumps(analysis, sort_keys=True))


if __name__ == "__main__":
    main()
