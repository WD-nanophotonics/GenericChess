"""Audit and summarize the frozen 5x5 static-vs-Unit panel without searches."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.core.actions import action_to_dict
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
    __import__("subprocess").run(
        ["git", "cat-file", "-e", PLAN["source_head"]], check=True
    )
    prior_seeds = set(range(521001, 521009)) | set(range(522001, 522009))
    assert set(PLAN["rules"]["seeds"]).isdisjoint(prior_seeds)
    producer_sha = hashlib.sha256((HERE / "producer.py").read_bytes()).hexdigest()
    source = json.loads((HERE / "producer-source.json").read_text(encoding="utf-8"))
    assert source["plan_sha256"] == plan_sha
    assert source["producer_sha256"] == producer_sha
    assert source["head"] == PLAN["source_head"]
    tracked_python = __import__("subprocess").check_output(
        ["git", "ls-files", "-z", "generic_chess"]
    ).split(b"\0")
    tracked_python = [p.decode("utf-8") for p in tracked_python if p]
    tree_digest = hashlib.sha256()
    for relative in tracked_python:
        tree_digest.update(relative.encode("utf-8") + b"\0")
        tree_digest.update(
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().encode("ascii") + b"\n"
        )
    assert len(tracked_python) == source["tracked_generic_chess_python_file_count"]
    assert tree_digest.hexdigest() == source["tracked_generic_chess_python_tree_sha256"]
    rules = {}
    compiled_by_seed = {}
    profile_hashes = {}
    signatures = defaultdict(list)
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
        compiled_by_seed[str(seed)] = compiled
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        expected_profile = record_value({
            "fingerprint": compiled.ruleset_fingerprint,
            "piece_profiles": profile.piece_profiles,
            "board": profile.board_value_by_type,
            "hand": profile.hand_value_by_base_type,
        })
        profile_path = HERE / f"profile-{seed}.json"
        observed_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        assert observed_profile == expected_profile
        profile_hashes[str(seed)] = hashlib.sha256(profile_path.read_bytes()).hexdigest()
        for type_id, item in profile.piece_profiles.items():
            signature = item.movement_signature
            signatures[signature].append({
                "seed": seed,
                "type_id": type_id,
                "raw_capability_score": float(item.raw_capability_score),
                "normalized_board_value": int(profile.board_value_by_type[type_id]),
                "normalized_hand_value": int(profile.hand_value_by_base_type[type_id]),
                "is_promotable": bool(item.is_promotable),
            })

    repeated_signatures = [
        {
            "movement_signature_sha256": hashlib.sha256(signature.encode("utf-8")).hexdigest(),
            "members": members,
        }
        for signature, members in sorted(signatures.items()) if len(members) > 1
    ]

    roots = json.loads((HERE / "roots.json").read_text(encoding="utf-8"))
    expected_roots = {}
    for seed in PLAN["rules"]["seeds"]:
        compiled = compiled_by_seed[str(seed)]
        for family in range(PLAN["roots"]["prefix_families_per_rule"]):
            rng = random.Random(seed * 1_000_000 + family)
            session = GameSession(compiled)
            opening = []
            for _ in range(PLAN["roots"]["prefix_plies"]):
                if session.result.status.value != "ongoing":
                    break
                legal = sorted(
                    session.legal_actions(),
                    key=lambda action: json.dumps(action_to_dict(action), sort_keys=True),
                )
                assert legal, "CORE_ONGOING_WITHOUT_LEGAL_ACTION_DURING_PREFIX"
                action = legal[rng.randrange(len(legal))]
                opening.append(action)
                session.submit(action)
            root_id = f"{seed}-{family}"
            expected_roots[root_id] = {
                "family": family,
                "rule_id": str(seed),
                "opening": [record_value(action) for action in opening],
                "root_sha256": digest(session.state),
                "prefix_seed": seed * 1_000_000 + family,
            }
    observed_roots = {row["root_id"]: row for row in roots}
    assert len(roots) == len(PLAN["rules"]["seeds"]) * PLAN["roots"]["prefix_families_per_rule"]
    assert set(observed_roots) == set(expected_roots)
    for root_id, expected in expected_roots.items():
        observed = observed_roots[root_id]
        assert all(observed[key] == value for key, value in expected.items())

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
    query_causes = Counter()
    query_budget_rows = defaultdict(list)
    cost_by_arm = {}
    replayed = 0
    for row in games:
        seed, family = row["game_id"].split("|", 1)[0].split("-")
        generated_ruleset, compiled = rules[seed]
        root_id = f"{seed}-{family}"
        expected_root = expected_roots[root_id]
        assert row["opening_actions"] == expected_root["opening"]
        assert row["root_state_sha256"] == expected_root["root_sha256"]
        serialized_rule = json.loads((HERE / f"rule-{seed}.json").read_text(encoding="utf-8"))
        assert ruleset_to_dict(generated_ruleset) == serialized_rule
        record = deserialize_game_record(json.dumps(row["final_record"]))
        session = GameSession.replay(compiled, record)
        assert digest(session.state) == row["final_state_sha256"]
        assert session.result.winner == row["winner"]
        if row["terminal_reason"] == "ACTUAL_TERMINAL":
            expected_reward = 0 if row["winner"] is None else (1 if row["winner"] == row["candidate_owner"] else -1)
            assert row["reward"] == expected_reward
            assert session.result.status.value != "ongoing"
        elif row["terminal_reason"] == "HORIZON_96_CANDIDATE_UNKNOWN":
            assert row["reward"] is None and row["candidate_plies"] == 96
            assert session.result.status.value == "ongoing"
        else:
            raise AssertionError(f"unplanned terminal classification: {row['terminal_reason']}")
        executed_events = sum("state_after" in move for move in row["moves"])
        assert (
            len(record.actions) - len(row["opening_actions"])
            + (1 if record.declaration is not None else 0)
            == executed_events
        )
        assert (row["terminal_reason"] == "NO_EXECUTABLE_RETURN_UNKNOWN") == (
            bool(row["moves"]) and "state_after" not in row["moves"][-1]
        )
        successful_candidate_plies = sum(
            move["role"] == "candidate" and "state_after" in move for move in row["moves"]
        )
        assert successful_candidate_plies == row["candidate_plies"]
        if row["terminal_reason"] == "HORIZON_96_CANDIDATE_UNKNOWN":
            assert row["candidate_plies"] == 96
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
    by_foe_owner = {}
    first_action_controls = {}
    by_seed = {}
    leave_one_seed_out = {}
    seed_bounds = defaultdict(list)
    pairs_by_foe_seed = defaultdict(list)
    for foe in PLAN["arms"]["fixed_foes"]:
        cost_by_arm[foe] = {}
        for candidate in PLAN["arms"]["candidates"]:
            arm_games = [g for g in games if g["foe"] == foe and g["candidate"] == candidate]
            candidate_moves = [m for g in arm_games for m in g["moves"] if m["role"] == "candidate"]
            foe_moves = [m for g in arm_games for m in g["moves"] if m["role"] == "foe"]
            cost_by_arm[foe][candidate] = {
                "games": len(arm_games),
                "candidate_queries": len(candidate_moves),
                "candidate_nodes": sum(int(m["nodes"]) for m in candidate_moves),
                "candidate_caller_seconds": sum(float(m["caller_seconds"]) for m in candidate_moves),
                "fixed_foe_queries": len(foe_moves),
                "fixed_foe_nodes": sum(int(m["nodes"]) for m in foe_moves),
                "fixed_foe_caller_seconds": sum(float(m["caller_seconds"]) for m in foe_moves),
                "unknown_games": sum(g["reward"] is None for g in arm_games),
                "actual_terminal_games": sum(g["terminal_reason"] == "ACTUAL_TERMINAL" for g in arm_games),
            }
        pairs = []
        pairs_by_owner = defaultdict(list)
        first_action_controls[foe] = {}
        for owner in (0, 1):
            paired_roots = 0
            shared_candidate_states = 0
            action_divergences = 0
            matching_actions = 0
            for root in sorted({g["game_id"].split("|", 1)[0] for g in games}):
                static_game = lookup[(root, foe, owner, "static_v2")]
                unit_game = lookup[(root, foe, owner, "unit")]
                static_queries = [m for m in static_game["moves"] if m["role"] == "candidate"]
                unit_queries = [m for m in unit_game["moves"] if m["role"] == "candidate"]
                if not static_queries or not unit_queries:
                    continue
                paired_roots += 1
                left, right = static_queries[0], unit_queries[0]
                if left["state_before"] != right["state_before"]:
                    continue
                shared_candidate_states += 1
                if left["action"] == right["action"]:
                    matching_actions += 1
                else:
                    action_divergences += 1
            first_action_controls[foe][str(owner)] = {
                "root_pairs_with_candidate_query": paired_roots,
                "same_first_candidate_state": shared_candidate_states,
                "first_actions_equal": matching_actions,
                "first_actions_differ": action_divergences,
                "interpretation": "Post hoc policy-operation diagnostic only; a changed first action is not itself a utility gain.",
            }
        for root in sorted({g["game_id"].split("|", 1)[0] for g in games}):
            for owner in (0, 1):
                static = lookup[(root, foe, owner, "static_v2")]
                unit = lookup[(root, foe, owner, "unit")]
                assert static["opening_actions"] == unit["opening_actions"]
                assert static["root_state_sha256"] == unit["root_state_sha256"]
                pair = (static["reward"], unit["reward"])
                pairs.append(pair)
                pairs_by_owner[owner].append(pair)
                seed = static["game_id"].split("|", 1)[0].split("-")[0]
                seed_bounds[(foe, seed)].append((static["reward"], unit["reward"]))
                pairs_by_foe_seed[(foe, seed)].append((static["reward"], unit["reward"]))
        summary = mean_bounds(pairs)
        summary.pop("finite_values")
        by_foe[foe] = summary
        by_foe_owner[foe] = {}
        for owner, owner_pairs in sorted(pairs_by_owner.items()):
            owner_summary = mean_bounds(owner_pairs)
            owner_summary.pop("finite_values")
            by_foe_owner[foe][str(owner)] = owner_summary
    for (foe, seed), rows in sorted(seed_bounds.items()):
        summary = mean_bounds(rows)
        by_seed[f"foe={foe}|seed={seed}"] = {
            k: summary[k] for k in ("pairs", "finite_pairs", "unknown_pairs", "finite_mean", "all_slot_lower", "all_slot_upper")
        }
    for foe in PLAN["arms"]["fixed_foes"]:
        seeds = sorted(seed for f, seed in pairs_by_foe_seed if f == foe)
        exclusions = {}
        for omitted in seeds:
            retained = [pair for seed in seeds if seed != omitted for pair in pairs_by_foe_seed[(foe, seed)]]
            summary = mean_bounds(retained)
            exclusions[omitted] = {
                k: summary[k] for k in ("pairs", "finite_pairs", "unknown_pairs", "finite_mean", "all_slot_lower", "all_slot_upper")
            }
        leave_one_seed_out[foe] = {
            "purpose": "Post hoc descriptive robustness check; not a confidence interval or population estimate.",
            "excluded_seed_summaries": exclusions,
            "minimum_lower_after_one_seed_exclusion": min(v["all_slot_lower"] for v in exclusions.values()),
            "maximum_upper_after_one_seed_exclusion": max(v["all_slot_upper"] for v in exclusions.values()),
        }

    for query in queries:
        query_causes[query["cause"]] += 1
        labels = dict(part.split("=", 1) for part in query["game_id"].split("|")[1:])
        query_budget_rows[(query["role"], labels["candidate"])].append(query)

    result = json.loads((HERE / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "COMPLETE" and result["unstarted_slots"] == 0
    assert result["actual_terminals"] == reasons["ACTUAL_TERMINAL"]
    assert result["unknown"] == sum(v for k, v in outcomes.items() if k == "UNKNOWN")
    analysis = {
        "schema": "primary-static-5x5-equal-d3-analysis-v1",
        "plan_sha256": plan_sha,
        "producer_sha256": producer_sha,
        "profile_file_sha256_by_seed": profile_hashes,
        "exact_movement_signature_census": {
            "profiles": len(profile_hashes),
            "nonanchor_entries": sum(len(v) for v in signatures.values()),
            "exact_classes": len(signatures),
            "repeated_exact_classes": repeated_signatures,
            "scope": "Exact serialized movement-signature equality only; no reflection or promotion equivalence inferred.",
        },
        "planned_slots": len(planned_ids), "returned_slots": len(games),
        "replayed_full_records": replayed, "query_records": len(queries),
        "query_termination_causes": dict(sorted(query_causes.items())),
        "queries_using_fallback": sum(bool(q["fallback"]) for q in queries),
        "query_budget_audit": {
            f"role={role}|candidate={candidate}": {
                "queries": len(rows),
                "configured_limits": PLAN["arms"]["candidate_budget" if role == "candidate" else "foe_budget"],
                "max_nodes": max(int(q["nodes"]) for q in rows),
                "max_depth": max(int(q["depth"]) for q in rows),
                "max_qnodes": max(int(q["qnodes"]) for q in rows),
                "max_caller_seconds": max(float(q["caller_seconds"]) for q in rows),
                "max_kernel_seconds": max(float(q["kernel_seconds"]) for q in rows),
                "over_node_cap": sum(int(q["nodes"]) > int(PLAN["arms"]["candidate_budget" if role == "candidate" else "foe_budget"]["max_nodes"]) for q in rows),
                "over_depth_cap": sum(int(q["depth"]) > int(PLAN["arms"]["candidate_budget" if role == "candidate" else "foe_budget"]["max_depth"]) for q in rows),
                "over_time_cap": sum(float(q["caller_seconds"]) > float(PLAN["arms"]["candidate_budget" if role == "candidate" else "foe_budget"]["max_time_seconds"]) for q in rows),
            }
            for (role, candidate), rows in sorted(query_budget_rows.items())
        },
        "terminal_reasons": dict(sorted(reasons.items())),
        "candidate_rewards": dict(sorted(outcomes.items())),
        "actual_action_kinds": dict(sorted(action_kinds.items())),
        "cost_by_fixed_foe_and_candidate": cost_by_arm,
        "planned_horizon_candidate_plies": 96,
        "implemented_candidate_horizon": 96,
        "maximum_observed_candidate_plies": max(
            sum(1 for m in g["moves"] if m["side"] == g["candidate_owner"] and "state_after" in m)
            for g in games
        ),
        "protocol_deviation": None,
        "fixed_foe_static_minus_unit": by_foe,
        "fixed_foe_by_candidate_owner": by_foe_owner,
        "first_candidate_action_diagnostic": first_action_controls,
        "linked_seed_families": by_seed,
        "leave_one_seed_out": leave_one_seed_out,
        "result_summary": result,
        "interpretation": "Finite paired evidence only for these 8 generated 5x5 rules and symmetric D3 fixed budgets; unknown slots retain [-1,1] per candidate outcome. Linked seed rows are descriptive, not population confidence.",
    }
    body = json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (HERE / "analysis.json").write_text(body, encoding="utf-8")
    print(json.dumps(analysis, sort_keys=True))


if __name__ == "__main__":
    main()
