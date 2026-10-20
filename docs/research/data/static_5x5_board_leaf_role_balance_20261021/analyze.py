"""Replay and analyze board-only outcomes with balanced first/reply roots; no searches."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
if Path.cwd().resolve() != ROOT:
    raise RuntimeError(f"RUN_FROM_REPOSITORY_ROOT:{ROOT}")
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
from producer import checkpoint as make_checkpoint

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))


def digest(value) -> str:
    raw = json.dumps(record_value(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def outcome_interval(rows, coefficients):
    lo_total = hi_total = 0.0
    finite = []
    for row in rows:
        lo = hi = 0.0
        all_finite = True
        finite_value = 0.0
        for arm, coefficient in coefficients.items():
            reward = row[arm]
            if reward is None:
                all_finite = False
                reward_lo, reward_hi = -1.0, 1.0
            else:
                reward_lo = reward_hi = float(reward)
                finite_value += coefficient * float(reward)
            if coefficient >= 0:
                lo += coefficient * reward_lo
                hi += coefficient * reward_hi
            else:
                lo += coefficient * reward_hi
                hi += coefficient * reward_lo
        lo_total += lo
        hi_total += hi
        if all_finite:
            finite.append(finite_value)
    n = len(rows)
    return {
        "paired_root_owner_cells": n,
        "finite_cells": len(finite),
        "unknown_cells": n - len(finite),
        "finite_mean": None if not finite else sum(finite) / len(finite),
        "all_slot_lower": lo_total / n,
        "all_slot_upper": hi_total / n,
    }


def main():
    plan_sha = hashlib.sha256((HERE / "plan.json").read_bytes()).hexdigest()
    producer_sha = hashlib.sha256((HERE / "producer.py").read_bytes()).hexdigest()
    source = json.loads((HERE / "producer-source.json").read_text(encoding="utf-8"))
    assert source["schema"] == PLAN["schema"]
    assert source["head"] == PLAN["source_head"]
    assert source["plan_sha256"] == plan_sha
    assert source["producer_sha256"] == producer_sha
    subprocess.run(["git", "cat-file", "-e", PLAN["source_head"]], check=True)

    tracked_python = subprocess.check_output(["git", "ls-files", "-z", "generic_chess"]).split(b"\0")
    tracked_python = [p.decode("utf-8") for p in tracked_python if p]
    tree = hashlib.sha256()
    for relative in tracked_python:
        tree.update(relative.encode("utf-8") + b"\0")
        tree.update(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest().encode("ascii") + b"\n")
    assert len(tracked_python) == source["tracked_generic_chess_python_file_count"]
    assert tree.hexdigest() == source["tracked_generic_chess_python_tree_sha256"]

    assert PLAN["schema"] == "primary-static-5x5-d3-board-leaf-role-balance-v1"
    assert PLAN["rules"]["seeds"] == [530301, 530302, 530303, 530304, 530305, 530306, 530308, 530310]
    preflight = json.loads((HERE / "seed-preflight.json").read_text(encoding="utf-8"))
    assert not set(PLAN["rules"]["seeds"]) & set(preflight["existing_plan_seeds"])
    assert not preflight["overlap"]
    assert PLAN["arms"]["candidates"] == ["unit_leaf__unit_order", "static_v2_leaf__unit_order"]
    assert PLAN["arms"]["fixed_foes"] == ["unit"]
    rules = {}
    profiles = {}
    checkpoints = {}
    generated_roots = {}
    for index, seed in enumerate(PLAN["rules"]["seeds"]):
        cfg = GeneratorConfig(
            seed=seed, board_size=5,
            setup_preset=PLAN["rules"]["setups_by_seed_order"][index % 3],
            movement_symmetry=PLAN["rules"]["movement_symmetry_by_seed_order"][index % 2],
            allow_hybrid=True, require_promotable_type=True,
            require_nonpromotable_type=True, max_generation_attempts=16,
            require_no_opening_win_in_one=False,
        )
        generated = generate_game(cfg)
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        rules[str(seed)] = (generated.ruleset, compiled)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        expected_profile = record_value({
            "fingerprint": compiled.ruleset_fingerprint,
            "piece_profiles": profile.piece_profiles,
            "board": profile.board_value_by_type,
            "hand": profile.hand_value_by_base_type,
        })
        profile_path = HERE / f"profile-{seed}.json"
        assert json.loads(profile_path.read_text(encoding="utf-8")) == expected_profile
        profiles[str(seed)] = profile
        checkpoints[str(seed)] = {
            kind: make_checkpoint(compiled, profile, kind)
            for kind in ("unit", "static_v2")
        }
        unit_cp = checkpoints[str(seed)]["unit"]
        board_cp = checkpoints[str(seed)]["static_v2"]
        assert board_cp.hand_weights == unit_cp.hand_weights
        assert not board_cp.dynamic_weights and not board_cp.spatial_occupancy_weights
        assert not board_cp.localized_control_weights and not board_cp.compact_nonlinear
        assert board_cp.board_weights == {t: v / 1000.0 for t, v in profile.board_value_by_type.items()}
        for family in range(PLAN["roots"]["prefix_families_per_rule"]):
            rng = random.Random(seed * 1_000_000 + family)
            session = GameSession(compiled)
            opening = []
            prefix_plies = PLAN["roots"]["prefix_plies_by_family"][family]
            for _ in range(prefix_plies):
                if session.result.status.value != "ongoing":
                    break
                legal = sorted(session.legal_actions(), key=lambda a: json.dumps(action_to_dict(a), sort_keys=True))
                assert legal
                action = legal[rng.randrange(len(legal))]
                opening.append(action)
                session.submit(action)
            root_id = f"{seed}-{family}"
            generated_roots[root_id] = {
                "root_id": root_id, "rule_id": str(seed), "family": family,
                "prefix_seed": seed * 1_000_000 + family,
                "prefix_plies": prefix_plies,
                "opening": [record_value(a) for a in opening],
                "root_sha256": digest(session.state),
            }

    roots = json.loads((HERE / "roots.json").read_text(encoding="utf-8"))
    expected_roots = {row["root_id"]: row for row in generated_roots.values()}
    assert {row["root_id"]: row for row in roots} == expected_roots
    assert len(roots) == len(PLAN["rules"]["seeds"]) * PLAN["roots"]["prefix_families_per_rule"]

    games = [json.loads(line) for line in (HERE / "games.jsonl").read_text(encoding="utf-8").splitlines() if line]
    queries = [json.loads(line) for line in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if line]
    queries_by_game = defaultdict(list)
    for query in queries:
        queries_by_game[query["game_id"]].append(
            {key: value for key, value in query.items() if key != "game_id"}
        )
    arms = PLAN["arms"]["candidates"]
    planned = {
        f"{root_id}|foe=unit|candidate={arm}|owner={owner}"
        for root_id in expected_roots for arm in arms for owner in (0, 1)
    }
    assert len(games) == PLAN["arms"]["physical_games"]
    assert {row["game_id"] for row in games} == planned
    assert len({row["game_id"] for row in games}) == len(games)
    assert len(queries) == sum(row["queries"] for row in games)

    terminal_reasons = Counter()
    rewards = Counter()
    fallback_queries = 0
    query_causes = Counter()
    queries_by_arm_role = defaultdict(list)
    action_kinds = Counter()
    replayed = 0
    paired = defaultdict(dict)
    turn_order = {}
    for row in games:
        root_id, rest = row["game_id"].split("|", 1)
        owner = int(rest.rsplit("owner=", 1)[1])
        labels = dict(part.split("=", 1) for part in rest.split("|"))
        arm = labels["candidate"]
        seed = root_id.split("-", 1)[0]
        generated_ruleset, compiled = rules[seed]
        assert json.loads((HERE / f"rule-{seed}.json").read_text(encoding="utf-8")) == ruleset_to_dict(generated_ruleset)
        root = expected_roots[root_id]
        assert row["opening_actions"] == root["opening"]
        assert row["root_state_sha256"] == root["root_sha256"]
        assert queries_by_game[row["game_id"]] == row["moves"], f"QUERY_GAME_MISMATCH:{row['game_id']}"
        for move in row["moves"]:
            expected_leaf = (
                arm.split("__", 1)[0].removesuffix("_leaf")
                if move["role"] == "candidate" else "unit"
            )
            assert move["leaf_checkpoint_id"] == checkpoints[seed][expected_leaf].checkpoint_id
            assert move["ordering_checkpoint_id"] == checkpoints[seed]["unit"].checkpoint_id
        record = deserialize_game_record(json.dumps(row["final_record"]))
        session = GameSession.replay(compiled, record)
        assert digest(session.state) == row["final_state_sha256"]
        assert session.result.winner == row["winner"]
        if row["terminal_reason"] == "ACTUAL_TERMINAL":
            expected_reward = 0 if row["winner"] is None else (1 if row["winner"] == owner else -1)
            assert row["reward"] == expected_reward and session.result.status.value != "ongoing"
        elif row["terminal_reason"] == "HORIZON_96_CANDIDATE_UNKNOWN":
            assert row["reward"] is None and row["candidate_plies"] == 96
            assert session.result.status.value == "ongoing"
        else:
            raise AssertionError(f"UNPLANNED_RESULT:{row['terminal_reason']}")
        assert sum(m["role"] == "candidate" and "state_after" in m for m in row["moves"]) == row["candidate_plies"]
        assert row["foe"] == "unit"
        paired[(root_id, owner)][arm] = row["reward"]
        first_role = row["moves"][0]["role"] if row["moves"] else "NO_SEARCH"
        prior_role = turn_order.setdefault((root_id, owner), first_role)
        assert prior_role == first_role, f"ARM_FIRST_ROLE_MISMATCH:{root_id}:{owner}"
        terminal_reasons[row["terminal_reason"]] += 1
        rewards["UNKNOWN" if row["reward"] is None else str(row["reward"])] += 1
        replayed += 1
        for move in row["moves"]:
            action = move.get("action")
            if action is not None:
                if "base_type_id" in action:
                    action_kinds["drop"] += 1
                else:
                    action_kinds["board"] += 1
                    if action.get("promotion_target_id") is not None:
                        action_kinds["promotion"] += 1
            queries_by_arm_role[(arm, move["role"])].append(move)
            fallback_queries += int(bool(move["fallback"]))
            query_causes[move["cause"]] += 1
    assert all(set(v) == set(arms) for v in paired.values())
    timing_cells = defaultdict(list)
    for key, rewards_by_arm in paired.items():
        role = turn_order[key]
        timing_cells[role].append(rewards_by_arm)
    games_by_cell = defaultdict(dict)
    for row in games:
        root_id = row["game_id"].split("|", 1)[0]
        games_by_cell[(root_id, int(row["candidate_owner"]))][row["candidate"]] = row
    first_action_audit = Counter()
    for key, rows_by_arm in games_by_cell.items():
        unit_row = rows_by_arm["unit_leaf__unit_order"]
        static_row = rows_by_arm["static_v2_leaf__unit_order"]
        unit_first = next((m for m in unit_row["moves"] if m["role"] == "candidate"), None)
        static_first = next((m for m in static_row["moves"] if m["role"] == "candidate"), None)
        assert (unit_first is None) == (static_first is None), f"CANDIDATE_FIRST_QUERY_MISMATCH:{key}"
        if unit_first is not None:
            assert unit_first["state_before"] == static_first["state_before"], f"CANDIDATE_FIRST_STATE_MISMATCH:{key}"
            first_action_audit["paired_candidate_first_queries"] += 1
            first_action_audit["candidate_first_state_matches"] += 1
            first_action_audit["first_action_changed"] += unit_first["action"] != static_first["action"]
        unit_path = [m.get("action") for m in unit_row["moves"]]
        static_path = [m.get("action") for m in static_row["moves"]]
        first_action_audit["full_action_path_changed"] += unit_path != static_path
        first_action_audit["candidate_action_sequence_changed"] += (
            [m.get("action") for m in unit_row["moves"] if m["role"] == "candidate"]
            != [m.get("action") for m in static_row["moves"] if m["role"] == "candidate"]
        )
    result = json.loads((HERE / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "COMPLETE" and result["unstarted_slots"] == 0
    assert result["full_history_replay_mismatches"] == 0

    contrast_specs = PLAN["contrasts"]
    coefficients = {k: v for k, v in contrast_specs.items() if isinstance(v, dict)}
    cells = [row for _, row in sorted(paired.items())]
    contrasts = {}
    for name, coeffs in coefficients.items():
        all_cells = outcome_interval(cells, coeffs)
        all_cells["by_candidate_first_role"] = {
            role: outcome_interval(rows, coeffs)
            for role, rows in sorted(timing_cells.items())
        }
        by_seed = {}
        for seed in PLAN["rules"]["seeds"]:
            subset = [row for (root_id, owner), row in sorted(paired.items()) if root_id.startswith(f"{seed}-")]
            by_seed[str(seed)] = outcome_interval(subset, coeffs)
        leave_one_out = {}
        for seed in PLAN["rules"]["seeds"]:
            subset = [row for (root_id, owner), row in sorted(paired.items()) if not root_id.startswith(f"{seed}-")]
            leave_one_out[str(seed)] = outcome_interval(subset, coeffs)
        all_cells.update({
            "by_candidate_owner": {
                str(owner): outcome_interval([row for (root_id, own), row in sorted(paired.items()) if own == owner], coeffs)
                for owner in (0, 1)
            },
            "by_seed": by_seed,
            "leave_one_seed_out": leave_one_out,
            "minimum_leave_one_seed_lower": min(v["all_slot_lower"] for v in leave_one_out.values()),
            "maximum_leave_one_seed_upper": max(v["all_slot_upper"] for v in leave_one_out.values()),
            "coefficients": coeffs,
        })
        contrasts[name] = all_cells

    budget_audit = {}
    for (arm, role), rows in sorted(queries_by_arm_role.items()):
        limits = PLAN["arms"]["candidate_budget" if role == "candidate" else "foe_budget"]
        budget_audit[f"arm={arm}|role={role}"] = {
            "queries": len(rows),
            "total_nodes": sum(int(q["nodes"]) for q in rows),
            "total_caller_seconds": sum(float(q["caller_seconds"]) for q in rows),
            "max_nodes": max(int(q["nodes"]) for q in rows),
            "max_depth": max(int(q["depth"]) for q in rows),
            "max_qnodes": max(int(q["qnodes"]) for q in rows),
            "max_caller_seconds": max(float(q["caller_seconds"]) for q in rows),
            "over_node_cap": sum(int(q["nodes"]) > limits["max_nodes"] for q in rows),
            "over_depth_cap": sum(int(q["depth"]) > limits["max_depth"] for q in rows),
            "over_time_cap": sum(float(q["caller_seconds"]) > limits["max_time_seconds"] for q in rows),
            "causes": dict(Counter(q["cause"] for q in rows)),
            "fallbacks": sum(bool(q["fallback"]) for q in rows),
        }

    analysis = {
        "schema": "primary-static-5x5-d3-board-leaf-role-balance-analysis-v1",
        "plan_sha256": plan_sha,
        "producer_sha256": producer_sha,
        "producer_source_sha256": hashlib.sha256((HERE / "producer-source.json").read_bytes()).hexdigest(),
        "planned_slots": len(planned), "returned_slots": len(games),
        "replayed_full_records": replayed,
        "validated_exact_shared_roots": len(expected_roots),
        "query_records": len(queries),
        "terminal_reasons": dict(terminal_reasons),
        "candidate_rewards": dict(rewards),
        "query_termination_causes": dict(query_causes),
        "queries_using_fallback": fallback_queries,
        "actual_action_kinds": dict(action_kinds),
        "budget_audit": budget_audit,
        "contrasts": contrasts,
        "candidate_turn_order_cells": dict(Counter(turn_order.values())),
        "first_candidate_action_audit": dict(first_action_audit),
        "result_summary": result,
        "interpretation": "Finite fresh-root board-only panel with Unit hand/no optional dynamic terms and both colors balanced across first/reply roles; roots differ by one opening ply, so role alignment remains descriptive. Independent unknown bounds are applied to each signed reward term. No population or global price/default claim.",
    }
    (HERE / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"contrasts": contrasts, "result": result, "fallbacks": fallback_queries, "budget_audit": budget_audit}, sort_keys=True))


if __name__ == "__main__":
    main()
