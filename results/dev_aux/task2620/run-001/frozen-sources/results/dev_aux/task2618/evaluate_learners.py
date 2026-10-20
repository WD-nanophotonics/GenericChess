"""Evaluate registered task2618 learner endpoints on actual Chess outcomes."""
from __future__ import annotations

from collections import Counter
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import time

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import restore


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/learner-comparison-v1"
RUN_NAMES = ("learner-comparison-v1", "learner-comparison-v2", "learner-comparison-v3", "learner-comparison-v4")
ENDPOINTS = ("initial", "TreeStrap", "TDLeaf", "WDL")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def learner_reward(white_outcome: int | None, learner_color: int) -> int | None:
    if learner_color not in (0, 1):
        raise ValueError("learner color must be 0 (White) or 1 (Black)")
    if white_outcome is None:
        return None
    if white_outcome not in (-1, 0, 1):
        raise ValueError("invalid actual Chess outcome")
    return white_outcome if learner_color == 0 else -white_outcome


def finite_reward_bounds(white_outcome: int | None, learner_color: int) -> tuple[int, int]:
    reward = learner_reward(white_outcome, learner_color)
    return (-1, 1) if reward is None else (reward, reward)


def verify_training_result(plan: dict, result: dict, expected_plan_sha: str) -> dict[tuple[int, str], dict]:
    if not result.get("eligible_for_evaluation") or result.get("status") != "COMPLETE_TRAINING":
        raise ValueError("evaluation requires every registered training arm to complete its paid-node budget")
    if result.get("plan_sha256") != expected_plan_sha:
        raise ValueError("training result is bound to another plan")
    arms = result.get("arms", [])
    expected = {(index, method) for index in range(len(plan["seeds"])) for method in plan["methods"]}
    actual = {(arm.get("seed_index"), arm.get("method")) for arm in arms}
    if actual != expected or len(arms) != len(expected):
        raise ValueError("training result does not contain exactly one endpoint for every seed/method")
    mapping = {(arm["seed_index"], arm["method"]): arm for arm in arms}
    for (seed_index, method), arm in mapping.items():
        if arm.get("status") not in {"NODE_BUDGET_REACHED", "NODE_BUDGET_REACHED_WITH_CENSORED_BLOCK"}:
            raise ValueError(f"training arm incomplete: {(seed_index, method)}")
        if arm.get("nodes_total") != plan["nodes_per_seed_method_arm"]:
            raise ValueError(f"training node budget mismatch: {(seed_index, method)}")
        weights = arm.get("final_weights")
        if not isinstance(weights, list) or len(weights) != 5 or weights[0] != 1.0:
            raise ValueError(f"invalid endpoint weight vector: {(seed_index, method)}")
    return mapping


def evaluate() -> dict:
    required = (RUN / "plan.json", RUN / "registration.json", RUN / "evaluation-root-manifest.json",
                RUN / "training-result.json", RUN / "evaluation-registration.json")
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("evaluation protocol is not registered or training is not complete")
    if any((RUN / name).exists() for name in ("evaluation-started.json", "evaluation-games.jsonl",
                                                "evaluation-queries.jsonl", "evaluation-result.json")):
        raise FileExistsError("evaluation outputs already exist; refusing rerun or top-up")
    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    registration = json.loads((RUN / "registration.json").read_text(encoding="utf-8"))
    eval_registration = json.loads((RUN / "evaluation-registration.json").read_text(encoding="utf-8"))
    if registration.get("status") != "REGISTERED_PRE_TRAINING" or registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("main learner plan registration mismatch")
    if registration.get("evaluation_root_manifest_sha256") != sha((RUN / "evaluation-root-manifest.json").read_bytes()):
        raise ValueError("evaluation root manifest changed")
    if eval_registration.get("status") != "REGISTERED_PRE_TRAINING" or eval_registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("evaluation registration mismatch")
    for relative, digest in plan["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"registered source changed: {relative}")
    if chess.__version__ != plan["python_chess_version"]:
        raise ValueError("python-chess runtime differs from registration")
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    role = json.loads((ROOT / ".local_agent/role.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("id") != plan["session_id"]:
        raise ValueError("evaluation requires the same active DEV_AUX segment")
    if role.get("role") != "DEV_AUX" or role.get("branch") != "sidemission":
        raise ValueError("evaluation must run in DEV_AUX/sidemission")

    training_raw = (RUN / "training-result.json").read_bytes()
    training = json.loads(training_raw)
    if eval_registration.get("training_result_sha256") != sha(training_raw):
        raise ValueError("the completed training result is not bound to this evaluation")
    arms = verify_training_result(plan, training, sha(plan_raw))
    initial_by_seed = {int(arm["seed"]): arm["initial_weights"] for arm in training["arms"]}
    roots_doc = json.loads((RUN / "evaluation-root-manifest.json").read_text(encoding="utf-8"))
    root_by_family = {row["family"]: row["record"] for row in roots_doc["roots"]}
    if len(root_by_family) != plan["evaluation"]["root_count"]:
        raise ValueError("evaluation root family count differs from the frozen plan")
    slots = plan["evaluation"]["ordered_slots"]
    if len(slots) != plan["evaluation"]["expected_slots"]:
        raise ValueError("registered evaluation slot count mismatch")
    if len(set(tuple(slot) for slot in slots)) != len(slots):
        raise ValueError("duplicate evaluation slot in registered order")
    caps_by_family = plan["evaluation"]["caps_by_family"]
    cap_values = set(plan["evaluation"]["cap_values_nodes_both_sides"])
    if set(map(int, caps_by_family)) != set(root_by_family):
        raise ValueError("every frozen evaluation root must have one cap")
    stop = SharedDeleteStopReader(ROOT)
    stop()
    began = time.perf_counter()
    started_record = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha(plan_raw),
        "registration_sha256": sha((RUN / "registration.json").read_bytes()),
        "evaluation_registration_sha256": sha((RUN / "evaluation-registration.json").read_bytes()),
        "training_result_sha256": sha(training_raw),
        "evaluation_roots_sha256": sha((RUN / "evaluation-root-manifest.json").read_bytes()),
        "source_sha256": plan["source_sha256"],
        "session_id": plan["session_id"],
    }
    with (RUN / "evaluation-started.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(started_record, indent=2, sort_keys=True) + "\n")

    counters = Counter()
    games = []
    status = "COMPLETE"
    with (RUN / "evaluation-games.jsonl").open("x", encoding="utf-8") as games_out, \
         (RUN / "evaluation-queries.jsonl").open("x", encoding="utf-8") as queries_out:
        for slot_index, slot in enumerate(slots):
            stop()
            seed_index, seed, family, learner_color, endpoint = slot
            if time.perf_counter() - began >= plan["evaluation"]["hard_cap_seconds"]:
                status = "PARTIAL_GLOBAL_CAP"
                break
            if endpoint == "initial":
                weights = initial_by_seed[seed]
            else:
                weights = arms[(seed_index, endpoint)]["final_weights"]
            learner = Model(weights)
            foe = Model(plan["fixed_foe_weights"])
            record = root_by_family[family]
            env = restore(0, None, record)
            if env.record() != record or env.terminal() is not None:
                raise ValueError(f"evaluation root failed exact replay: {family}")
            initial_record = env.record()
            nodes = searches = 0
            ending = "HORIZON_UNKNOWN"
            effective_slot_cap = caps_by_family[str(family)]
            if effective_slot_cap not in cap_values:
                raise ValueError(f"unregistered evaluation cap for family {family}")
            outcome = None
            for ply in range(plan["evaluation"]["max_plies_per_game"]):
                stop()
                outcome = env.terminal()
                if outcome is not None:
                    ending = "ACTUAL_TERMINAL"
                    break
                global_left = plan["evaluation"]["hard_cap_seconds"] - (time.perf_counter() - began)
                slot_left = effective_slot_cap - nodes
                if global_left <= 0:
                    status, ending = "PARTIAL_GLOBAL_CAP", "GLOBAL_CAP_UNKNOWN"
                    break
                if slot_left <= 0:
                    ending = "SLOT_NODE_CAP_UNKNOWN"
                    break
                actor = env.player()
                candidate_turn = actor == learner_color
                current = learner if candidate_turn else foe
                record_before = env.record()
                query_nodes = min(plan["evaluation"]["nodes_per_search"], slot_left)
                query_seconds = min(plan["evaluation"]["seconds_per_search"], global_left)
                ordering_seed = plan["evaluation"]["ordering_seed_base"] + seed * 1_000_000 + family * 1_000 + ply
                receipt = TrainingSearch(
                    plan["evaluation"]["depth"], quiet=False,
                    q_limit=plan["evaluation"]["q_limit"],
                ).search(env, current, nodes=query_nodes, seconds=query_seconds,
                         seed=ordering_seed, cancel=stop)
                if env.record() != record_before:
                    raise AssertionError("evaluation search mutated the board/history")
                if receipt.nodes < 0 or receipt.nodes > query_nodes:
                    raise AssertionError("evaluation search exceeded its requested node limit")
                nodes += receipt.nodes
                searches += 1
                if receipt.complete:
                    env.push(receipt.action)
                query = {
                    "slot_index": slot_index,
                    "slot": slot,
                    "family_cap_nodes_both_sides": effective_slot_cap,
                    "ply": ply,
                    "actor": actor,
                    "learner_color": learner_color,
                    "endpoint": endpoint,
                    "weights": list(current.weights),
                    "record_before": record_before,
                    "record_after": env.record(),
                    "complete": receipt.complete,
                    "action": None if not receipt.complete else receipt.action.uci(),
                    "value": receipt.value,
                    "nodes": receipt.nodes,
                    "total_slot_nodes_both_sides": nodes,
                    "seconds": receipt.seconds,
                    "effective_nodes": query_nodes,
                    "effective_seconds": query_seconds,
                    "ordering_seed": ordering_seed,
                    "search_stats": receipt.reason,
                }
                queries_out.write(json.dumps(query, sort_keys=True, allow_nan=False) + "\n")
                queries_out.flush()
                if not receipt.complete:
                    ending = "SEARCH_RESOURCE_UNKNOWN"
                    break
            outcome = env.terminal()
            if outcome is not None:
                ending = "ACTUAL_TERMINAL"
            replay = restore(0, None, env.record())
            if replay.record() != env.record() or replay.terminal() != outcome:
                raise AssertionError("evaluation game failed full-history Chess replay")
            row = {
                "slot_index": slot_index,
                "slot": slot,
                "family_cap_nodes_both_sides": effective_slot_cap,
                "endpoint": endpoint,
                "seed": seed,
                "seed_index": seed_index,
                "family": family,
                "learner_color": learner_color,
                "weights": list(weights),
                "initial_record": initial_record,
                "final_record": env.record(),
                "outcome_white_relative": outcome,
                "learner_reward": learner_reward(outcome, learner_color),
                "reward_bounds": list(finite_reward_bounds(outcome, learner_color)),
                "unknown_is_draw": False,
                "ending": ending,
                "nodes": nodes,
                "searches": searches,
            }
            games.append(row)
            games_out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            games_out.flush()
            counters.update(actual_terminal=outcome is not None, unknown=outcome is None, nodes=nodes, queries=searches)
            if status != "COMPLETE":
                break

    seen = {row["slot_index"] for row in games}
    missing = [index for index in range(len(slots)) if index not in seen]
    result = {
        "task": plan["task"],
        "status": status,
        "expected_slots": len(slots),
        "actual_slots": len(games),
        "missing_slots": missing,
        "actual_terminal": counters["actual_terminal"],
        "unknown": counters["unknown"],
        "nodes": counters["nodes"],
        "queries": counters["queries"],
        "seconds": time.perf_counter() - began,
        "unknown_is_draw": False,
        "all_slots_recorded_or_explicitly_missing": len(games) + len(missing) == len(slots),
        "training_result_sha256": sha(training_raw),
        "plan_sha256": sha(plan_raw),
        "interpretation": "Finite held-out-in-input exact-history Chess start panel against one fixed foe; terminal W/D/L only. Exact start disjointness does not establish descendant/transposition or population independence.",
    }
    with (RUN / "evaluation-result.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", choices=RUN_NAMES, default=RUN_NAMES[0])
    args = parser.parse_args()
    RUN = ROOT / "results/dev_aux/task2618" / args.run_name
    print(json.dumps(evaluate(), indent=2, sort_keys=True, allow_nan=False))
