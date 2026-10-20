"""Bounded cost-only WDL scan on prospective training roots.

The four paired terminal outcomes in each block update WDL proposals only in
memory.  This runner intentionally persists no outcomes, interval decisions,
or learned coefficients; it measures the shared task2612 AlphaBeta/Receipt
path and all-side node cost, not learner strength.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import time
from pathlib import Path

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import AlphaBeta, Model
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.wdl_receipt_adapter import (
    EPISODE_ORDER,
    accept_proposal,
    charge_nodes,
    initial_weights,
    propose,
)


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/wdl-shared-cost"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_plan() -> tuple[dict, dict]:
    plan_path = RUN / "plan.json"
    registration_path = RUN / "registration.json"
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    assert registration["status"] == "REGISTERED_COST_ONLY"
    assert registration["search_started"] is False
    assert plan["status"] == "FROZEN_BEFORE_SEARCH"
    assert plan["fitness_evaluation"] is False
    assert plan["root_indices"] == list(range(32))
    assert plan["episode_order"] == [[v, c] for v, c in EPISODE_ORDER]
    assert registration["plan_sha256"] == sha_bytes(plan_bytes)
    assert registration["session_id"] == plan["session_id"]
    for output_name in ("started.json", "episodes.jsonl", "result.json"):
        assert not (RUN / output_name).exists(), output_name
    assert not (RUN / "result.json").exists()
    for name, digest in plan["source_sha256"].items():
        assert sha_file(ROOT / name) == digest, name
    roots_path = ROOT / plan["training_roots_path"]
    assert sha_file(roots_path) == plan["training_roots_sha256"]
    assert chess.__version__ == plan["python_chess_version"]
    return plan, json.loads(roots_path.read_text(encoding="utf-8"))["roots"]


def run() -> dict:
    plan, root_rows = load_plan()
    if len(root_rows) < plan["seed_count"] * plan["proposal_rounds"]:
        raise ValueError("frozen training root pool is too small")
    stop = SharedDeleteStopReader(ROOT)
    stop()
    started = time.perf_counter()
    start_record = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha_file(RUN / "plan.json"),
        "registration_sha256": sha_file(RUN / "registration.json"),
        "source_sha256": plan["source_sha256"],
        "training_roots_sha256": plan["training_roots_sha256"],
        "python_chess_version": chess.__version__,
        "session_id": plan["session_id"],
    }
    with (RUN / "started.json").open("x", encoding="utf-8") as started_file:
        started_file.write(json.dumps(start_record, indent=2, sort_keys=True) + "\n")

    arm_rows = []
    status = "COMPLETE_COST_ONLY"
    with (RUN / "episodes.jsonl").open("x", encoding="utf-8") as episodes:
        for seed_index, seed in enumerate(plan["seeds"]):
            stop()
            began_arm = time.perf_counter()
            nodes_candidate = nodes_foe = searches = complete_searches = 0
            actual_terminal_episodes = unknown_episodes = paired_blocks = 0
            games = 0
            pending: list[dict] = []
            weights = initial_weights(seed)
            proposal_weights: list[float] | None = None
            arm_status = "MAX_PROPOSAL_ROUNDS_COST_ONLY"

            for round_index in range(plan["proposal_rounds"]):
                if time.perf_counter() - started >= plan["global_hard_cap_seconds"]:
                    status = "PARTIAL_GLOBAL_CAP"
                    arm_status = "GLOBAL_CAP_UNKNOWN"
                    break
                proposal_weights = propose(weights, seed, round_index)
                root_index = seed_index * plan["proposal_rounds"] + round_index
                root_row = root_rows[root_index]
                record = root_row["record"]
                root_key = sha_bytes(json.dumps(
                    record, sort_keys=True, separators=(",", ":")
                ).encode("utf-8"))

                for slot, (variant, candidate_color) in enumerate(EPISODE_ORDER):
                    stop()
                    if time.perf_counter() - started >= plan["global_hard_cap_seconds"]:
                        status = "PARTIAL_GLOBAL_CAP"
                        arm_status = "GLOBAL_CAP_UNKNOWN"
                        break
                    spent = nodes_candidate + nodes_foe
                    remaining = plan["node_budget_per_seed"] - spent
                    if remaining <= 0:
                        arm_status = "NODE_BUDGET_PARTIAL_BLOCK"
                        break

                    env = restore(0, None, record)
                    if env.record() != record or env.terminal() is not None:
                        raise ValueError("registered eight-ply root failed replay")
                    game_nodes_candidate = game_nodes_foe = game_searches = 0
                    ending = "HORIZON_UNKNOWN"
                    white_outcome = None
                    episode_start_wall = time.perf_counter()

                    for ply in range(plan["max_plies_per_game"]):
                        stop()
                        terminal = env.terminal()
                        if terminal is not None:
                            white_outcome = terminal
                            ending = "ACTUAL_TERMINAL_LABEL_CENSORED"
                            break
                        spent = nodes_candidate + nodes_foe
                        remaining = plan["node_budget_per_seed"] - spent
                        wall_remaining = plan["global_hard_cap_seconds"] - (
                            time.perf_counter() - started
                        )
                        if remaining <= 0:
                            ending = "AGGREGATE_NODE_CAP_UNKNOWN"
                            break
                        if wall_remaining <= 0:
                            ending = "GLOBAL_CAP_UNKNOWN"
                            status = "PARTIAL_GLOBAL_CAP"
                            arm_status = "GLOBAL_CAP_UNKNOWN"
                            break

                        is_candidate_actor = env.player() == candidate_color
                        episode_weights = (
                            weights if variant == "incumbent" else proposal_weights
                        )
                        model = Model(episode_weights)
                        receipt = AlphaBeta(2, 0).search(
                            env,
                            model,
                            nodes=min(plan["max_nodes_per_search"], remaining),
                            seconds=min(plan["seconds_per_search_cap"], wall_remaining),
                            seed=(seed * 1_000_000 + round_index * 10_000
                                  + slot * 1_000 + ply),
                            cancel=stop,
                        )
                        searches += 1
                        game_searches += 1
                        nodes_candidate, nodes_foe = charge_nodes(
                            nodes_candidate,
                            nodes_foe,
                            is_candidate_actor,
                            receipt.nodes,
                            plan["node_budget_per_seed"],
                        )
                        if is_candidate_actor:
                            game_nodes_candidate += receipt.nodes
                        else:
                            game_nodes_foe += receipt.nodes
                        if not receipt.complete:
                            ending = "SEARCH_RESOURCE_UNKNOWN"
                            break
                        complete_searches += 1
                        env.push(receipt.action)
                    else:
                        if env.terminal() is not None:
                            white_outcome = env.terminal()
                            ending = "ACTUAL_TERMINAL_LABEL_CENSORED"
                        else:
                            ending = "MAX_PLY_UNKNOWN"

                    if white_outcome is None:
                        unknown_episodes += 1
                    else:
                        actual_terminal_episodes += 1
                    row = {
                        "seed": seed,
                        "round_index": round_index,
                        "slot": slot,
                        "variant": variant,
                        "candidate_color": candidate_color,
                        "training_family": root_row["family"],
                        "root_sha256": root_key,
                        "candidate_nodes": game_nodes_candidate,
                        "fixed_foe_nodes": game_nodes_foe,
                        "total_nodes": game_nodes_candidate + game_nodes_foe,
                        "searches": game_searches,
                        "ending": ending,
                        "wall_seconds": time.perf_counter() - episode_start_wall,
                        "terminal_label_or_model_weights_emitted": False,
                    }
                    episodes.write(json.dumps(row, sort_keys=True) + "\n")
                    episodes.flush()
                    games += 1
                    pending.append({
                        "variant": variant,
                        "color": candidate_color,
                        "white_outcome": white_outcome,
                        "root_key": root_key,
                    })

                    if ending not in ("ACTUAL_TERMINAL_LABEL_CENSORED",):
                        arm_status = ending
                        break

                if status == "PARTIAL_GLOBAL_CAP" or len(pending) < 4:
                    break
                accepted, _interval = accept_proposal(pending)
                if accepted:
                    weights = list(proposal_weights)
                paired_blocks += 1
                pending.clear()

                if nodes_candidate + nodes_foe >= plan["node_budget_per_seed"]:
                    arm_status = "NODE_BUDGET_REACHED"
                    break

            arm_rows.append({
                "seed": seed,
                "arm_index": seed_index,
                "status": arm_status,
                "games": games,
                "paired_blocks_completed": paired_blocks,
                "incomplete_block_slots": len(pending),
                "candidate_nodes": nodes_candidate,
                "fixed_foe_nodes": nodes_foe,
                "total_nodes": nodes_candidate + nodes_foe,
                "searches": searches,
                "complete_searches": complete_searches,
                "actual_terminal_episodes": actual_terminal_episodes,
                "unknown_or_partial_episodes": unknown_episodes,
                "wall_seconds": time.perf_counter() - began_arm,
                "terminal_outcomes_or_coefficients_emitted": False,
            })
            if status == "PARTIAL_GLOBAL_CAP":
                break

    result = {
        "task": "DEV_AUX2618_WDL_SHARED_PATH_COST_ONLY",
        "status": status,
        "plan_sha256": sha_file(RUN / "plan.json"),
        "registration_sha256": sha_file(RUN / "registration.json"),
        "started_sha256": sha_file(RUN / "started.json"),
        "source_sha256": plan["source_sha256"],
        "training_roots_sha256": plan["training_roots_sha256"],
        "wall_seconds": time.perf_counter() - started,
        "arm_count": len(arm_rows),
        "arms": arm_rows,
        "fitness_evaluation": False,
        "terminal_outcomes_or_coefficients_emitted": False,
        "interpretation": (
            "Outcome labels were used only in-memory for registered WDL proposal "
            "updates. This is a shared AlphaBeta/Receipt cost/path scan, not a "
            "strength result, and does not authorize full learner registration."
        ),
    }
    with (RUN / "result.json").open("x", encoding="utf-8") as result_file:
        result_file.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
