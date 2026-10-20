"""Shared-AlphaBeta Chess learner training runner for task2618.

Inert until a separate write-once registration binds the active DEV_AUX segment,
all sources and roots. The runner never chooses roots or parameters from outcomes.
"""
from __future__ import annotations

from collections import Counter
import datetime
import hashlib
import json
import math
from pathlib import Path
import time

import chess

from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.learning import AlphaBeta, Model, TreeStrap
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2618.wdl_receipt_adapter import (
    EPISODE_ORDER,
    accept_proposal,
    initial_weights,
    propose,
)


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2618/learner-comparison-v1"
METHODS = ("TreeStrap", "TDLeaf", "WDL")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_number(value: float | int | None) -> float | int | str | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return value


def bound_counts(receipt) -> dict[str, int]:
    result = {"exact": 0, "lower_only": 0, "upper_only": 0}
    for sample in receipt.samples:
        if sample.lower == sample.upper:
            result["exact"] += 1
        elif sample.upper == math.inf:
            result["lower_only"] += 1
        elif sample.lower == -math.inf:
            result["upper_only"] += 1
        else:
            raise ValueError("unexpected finite interval sample in alpha-beta receipt")
    return result


def episode_root_rows(plan: dict, root_rows: list[dict], seed_index: int) -> list[dict]:
    roots_per_seed = plan["roots_per_seed"]
    first = seed_index * roots_per_seed
    rows = root_rows[first:first + roots_per_seed]
    if len(rows) != roots_per_seed:
        raise ValueError("registered training root block is incomplete")
    return rows


def missing_slot(*, method: str, seed_index: int, seed: int, family: int,
                 game_index: int, variant: str, learner_color: int, reason: str) -> dict:
    return {
        "method": method,
        "seed_index": seed_index,
        "seed": seed,
        "game_index": game_index,
        "family": family,
        "variant": variant,
        "learner_color": learner_color,
        "initial_record": None,
        "final_record": None,
        "outcome_white_relative": None,
        "ending": reason,
        "candidate_nodes": 0,
        "foe_nodes": 0,
        "episode_nodes": 0,
        "searches": 0,
        "training_loss_mean": None,
        "training_loss_terms": 0,
        "unstarted": True,
    }


def make_learner(method: str, plan: dict):
    if method == "TreeStrap":
        return TreeStrap(plan["learner_parameters"][method]["eta"])
    if method == "TDLeaf":
        values = plan["learner_parameters"][method]
        return TDLeafEpisode(values["eta"], values["lambda"])
    if method == "WDL":
        return None
    raise ValueError(f"unrecognized learner method {method!r}")


def validate_registration() -> tuple[dict, dict, dict]:
    required = (RUN / "plan.json", RUN / "registration.json", RUN / "root-manifest.json")
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("learner-comparison-v1 is not fully registered")
    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    registration = json.loads((RUN / "registration.json").read_text(encoding="utf-8"))
    root_manifest = json.loads((RUN / "root-manifest.json").read_text(encoding="utf-8"))
    if registration.get("status") != "REGISTERED_PRE_TRAINING":
        raise ValueError("registration is not eligible for training")
    if registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registered plan hash mismatch")
    if registration.get("session_id") != plan.get("session_id"):
        raise ValueError("registration/session mismatch")
    if plan.get("status") != "FROZEN_BEFORE_SEARCH" or plan.get("task") != "DEV_AUX2618_CHESS_LEARNER_COMPARISON":
        raise ValueError("unexpected task protocol")
    if plan.get("methods") != list(METHODS):
        raise ValueError("unexpected registered learner order")
    if registration.get("root_manifest_sha256") != sha((RUN / "root-manifest.json").read_bytes()):
        raise ValueError("root manifest hash mismatch")
    if plan.get("source_sha256") != registration.get("source_sha256"):
        raise ValueError("source hash map mismatch")
    for relative, digest in plan["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError(f"registered source changed: {relative}")
    if chess.__version__ != plan["python_chess_version"]:
        raise ValueError("python-chess version differs from registration")
    output_names = (
        "started.json", "queries.jsonl", "games.jsonl", "proposal-blocks.jsonl",
        "training-result.json", "evaluation-started.json", "evaluation-games.jsonl",
        "evaluation-queries.jsonl", "evaluation-result.json",
    )
    if any((RUN / name).exists() for name in output_names):
        raise FileExistsError("training outputs already exist; refusing rerun/top-up")
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    role = json.loads((ROOT / ".local_agent/role.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("id") != plan.get("session_id"):
        raise ValueError("training requires the same active registered DEV_AUX segment")
    if role.get("role") != "DEV_AUX" or role.get("branch") != "sidemission":
        raise ValueError("training must run in DEV_AUX/sidemission")
    if root_manifest.get("status") != "FROZEN_BEFORE_TRAINING":
        raise ValueError("training root manifest is not frozen")
    if len(root_manifest.get("roots", [])) != plan["roots_per_seed"] * len(plan["seeds"]):
        raise ValueError("training root manifest does not match the frozen seed blocks")
    return plan, registration, root_manifest


def play_episode(
    *,
    plan: dict,
    method: str,
    seed: int,
    game_index: int,
    family: int,
    record: dict,
    learner_color: int,
    candidate: Model,
    foe: Model,
    variant: str,
    tree: TreeStrap | None,
    td: TDLeafEpisode | None,
    arm_counts: dict,
    started: float,
    global_started: float,
    stop,
) -> tuple[dict, list[dict], dict]:
    env = restore(0, None, record)
    if env.record() != record or env.terminal() is not None:
        raise ValueError(f"registered root no longer replays: family={family}")
    initial_record = env.record()
    episode_initial_weights = list(candidate.weights)
    nodes_before = arm_counts["candidate_nodes"] + arm_counts["foe_nodes"]
    episode_start = time.perf_counter()
    if td is not None:
        td.reset()
    tree_samples = tree_active = td_observations = update_steps = 0
    loss_sum = loss_terms = 0.0
    queries: list[dict] = []
    ending = "HORIZON_UNKNOWN"
    outcome = None
    max_plies = plan["max_plies_per_game"]

    for ply in range(max_plies):
        stop()
        outcome = env.terminal()
        if outcome is not None:
            ending = "ACTUAL_TERMINAL"
            break
        elapsed_global = time.perf_counter() - global_started
        if elapsed_global >= plan["training_hard_cap_seconds"]:
            ending = "GLOBAL_TRAINING_CAP_UNKNOWN"
            break
        paid = arm_counts["candidate_nodes"] + arm_counts["foe_nodes"]
        left = plan["nodes_per_seed_method_arm"] - paid
        if left <= 0:
            ending = "NODE_BUDGET_UNKNOWN"
            break

        actor = env.player()
        candidate_turn = actor == learner_color
        search_model = candidate if candidate_turn else foe
        record_before = env.record()
        query_cap = min(plan["max_nodes_per_search"], left)
        seconds_left = plan["training_hard_cap_seconds"] - elapsed_global
        effective_seconds = min(plan["seconds_per_search_cap"], seconds_left)
        ordering_seed = (
            plan["ordering_seed_base"] + seed * 1_000_000 + family * 1_000 + ply
        )
        receipt = AlphaBeta(plan["search"]["depth"], plan["search"]["qdepth"]).search(
            env,
            search_model,
            nodes=query_cap,
            seconds=effective_seconds,
            seed=ordering_seed,
            cancel=stop,
        )
        if env.record() != record_before:
            raise AssertionError("search mutated the complete game history")
        if receipt.nodes < 0 or receipt.nodes > query_cap:
            raise AssertionError("search exceeded its registered node budget")
        actor_bucket = "candidate_nodes" if candidate_turn else "foe_nodes"
        arm_counts[actor_bucket] += receipt.nodes
        arm_counts["searches"] += 1
        if receipt.complete:
            arm_counts["complete_searches"] += 1
        else:
            arm_counts["incomplete_searches"] += 1

        stats = {"samples": 0, "active": 0, "loss": None, "changed": False}
        if receipt.complete and candidate_turn and tree is not None:
            stats = tree.update(candidate, receipt)
            tree_samples += stats["samples"]
            tree_active += stats["active"]
            update_steps += int(stats["changed"])
            if stats["loss"] is not None:
                loss_sum += stats["loss"] * stats["samples"]
                loss_terms += stats["samples"]
        elif receipt.complete and candidate_turn and td is not None:
            stats = td.observe(candidate, receipt)
            td_observations += int(receipt.complete)

        if receipt.complete:
            env.push(receipt.action)
        else:
            ending = "SEARCH_RESOURCE_UNKNOWN"

        queries.append({
            "method": method,
            "variant": variant,
            "seed": seed,
            "game_index": game_index,
            "family": family,
            "learner_color": learner_color,
            "ply": ply,
            "actor": actor,
            "candidate_turn": candidate_turn,
            "weights_before_search": list(search_model.weights),
            "record_before": record_before,
            "record_after": env.record(),
            "complete": receipt.complete,
            "action": None if not receipt.complete else receipt.action.uci(),
            "value": json_number(receipt.value),
            "pv_phi": receipt.pv_phi,
            "pv_terminal": receipt.pv_terminal,
            "tree_samples": stats["samples"],
            "tree_active_samples": stats["active"],
            "search_bound_sample_counts": bound_counts(receipt),
            "training_loss": stats["loss"],
            "nodes": receipt.nodes,
            "candidate_nodes_paid": arm_counts["candidate_nodes"],
            "foe_nodes_paid": arm_counts["foe_nodes"],
            "seconds": receipt.seconds,
            "effective_nodes": query_cap,
            "effective_seconds": effective_seconds,
            "ordering_seed": ordering_seed,
            "reason": receipt.reason,
        })
        if not receipt.complete:
            break

    actual = env.terminal()
    if actual is not None:
        outcome = actual
        ending = "ACTUAL_TERMINAL"
        arm_counts["actual_terminal_games"] += 1
    else:
        outcome = None
        arm_counts["unknown_games"] += 1

    td_stats = None
    if td is not None:
        td_stats = td.finish(candidate, outcome)
        update_steps += int(td_stats["changed"])
        if td_stats["loss"] is not None:
            loss_sum += td_stats["loss"] * td_stats["samples"]
            loss_terms += td_stats["samples"]
        arm_counts["update_steps"] += update_steps
        arm_counts["td_observations"] += td_observations
    if tree is not None:
        arm_counts["tree_samples"] += tree_samples
        arm_counts["tree_active_samples"] += tree_active
        arm_counts["update_steps"] += update_steps
    arm_counts["training_loss_sum"] = arm_counts.get("training_loss_sum", 0.0) + loss_sum
    arm_counts["training_loss_terms"] = arm_counts.get("training_loss_terms", 0) + int(loss_terms)

    replay = restore(0, None, env.record())
    if replay.record() != env.record() or replay.terminal() != actual:
        raise AssertionError("post-game Chess history replay mismatch")
    result = {
        "method": method,
        "variant": variant,
        "seed": seed,
        "game_index": game_index,
        "family": family,
        "learner_color": learner_color,
        "initial_record": initial_record,
        "weights_at_episode_start": episode_initial_weights,
        "weights_at_episode_end": list(candidate.weights),
        "final_record": env.record(),
        "outcome_white_relative": outcome,
        "ending": ending,
        "candidate_nodes": arm_counts["candidate_nodes"],
        "foe_nodes": arm_counts["foe_nodes"],
        "episode_nodes": arm_counts["candidate_nodes"] + arm_counts["foe_nodes"] - nodes_before,
        "searches": len(queries),
        "tree_samples": tree_samples,
        "tree_active_samples": tree_active,
        "td_observations": td_observations,
        "update_steps": update_steps,
        "training_loss_mean": loss_sum / loss_terms if loss_terms else None,
        "training_loss_terms": int(loss_terms),
        "td_terminal_stats": td_stats,
        "wall_seconds": time.perf_counter() - episode_start,
    }
    return result, queries, {"outcome": outcome, "ending": ending}


def _run_arm(plan: dict, roots: list[dict], seed_index: int, seed: int, method: str,
             global_started: float, stop, queries_out, games_out, blocks_out) -> dict:
    rows = episode_root_rows(plan, roots, seed_index)
    weights = initial_weights(seed)
    candidate = Model(weights)
    foe = Model(plan["fixed_foe_weights"])
    learner = make_learner(method, plan)
    counts = Counter({
        "candidate_nodes": 0,
        "foe_nodes": 0,
        "searches": 0,
        "complete_searches": 0,
        "incomplete_searches": 0,
        "actual_terminal_games": 0,
        "unknown_games": 0,
    })
    started = time.perf_counter()
    loss_sum = loss_terms = 0
    accepted = rejected = proposals = completed_blocks = 0
    games = 0
    status = "NODE_BUDGET_REACHED"

    planned_slots = 0
    recorded_wdl_slots: set[tuple[int, int]] = set()
    for game_index, root_row in enumerate(rows):
        stop()
        if time.perf_counter() - global_started >= plan["training_hard_cap_seconds"]:
            status = "GLOBAL_TRAINING_CAP_PARTIAL"
            break
        paid = counts["candidate_nodes"] + counts["foe_nodes"]
        if paid >= plan["nodes_per_seed_method_arm"]:
            status = "NODE_BUDGET_REACHED"
            break
        family = root_row["family"]
        record = root_row["record"]

        if method == "WDL":
            incumbent = Model(weights)
            proposal = Model(propose(weights, seed, game_index))
            pending: list[dict] = []
            block_games: list[dict] = []
            for slot, (variant, color) in enumerate(EPISODE_ORDER):
                paid = counts["candidate_nodes"] + counts["foe_nodes"]
                if paid >= plan["nodes_per_seed_method_arm"] or time.perf_counter() - global_started >= plan["training_hard_cap_seconds"]:
                    status = "INCOMPLETE_PAIRED_BLOCK_CENSORED"
                    break
                current = incumbent if variant == "incumbent" else proposal
                row, query_rows, end = play_episode(
                    plan=plan, method=method, seed=seed, game_index=game_index * 4 + slot,
                    family=family, record=record, learner_color=color, candidate=current,
                    foe=foe, variant=variant, tree=None, td=None, arm_counts=counts,
                    started=started, global_started=global_started, stop=stop,
                )
                games_out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                games_out.flush()
                for query in query_rows:
                    queries_out.write(json.dumps(query, sort_keys=True, allow_nan=False) + "\n")
                queries_out.flush()
                games += 1
                planned_slots += 1
                recorded_wdl_slots.add((game_index, slot))
                block_games.append(row)
                pending.append({
                    "variant": variant,
                    "color": color,
                    "white_outcome": end["outcome"],
                    "root_key": sha(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()),
                })
                if end["ending"] == "SEARCH_RESOURCE_UNKNOWN":
                    status = "INCOMPLETE_PAIRED_BLOCK_CENSORED"
                    break
            if len(pending) != 4:
                blocks_out.write(json.dumps({
                    "seed_index": seed_index,
                    "seed": seed,
                    "method": method,
                    "round": game_index,
                    "family": family,
                    "status": "INCOMPLETE_PAIRED_BLOCK_CENSORED",
                    "started_slots": len(block_games),
                    "expected_slots": len(EPISODE_ORDER),
                    "proposal_weights": proposal.weights,
                    "incumbent_weights_after": weights,
                    "accepted": False,
                    "interval_proposal_minus_incumbent": None,
                }, sort_keys=True, allow_nan=False) + "\n")
                blocks_out.flush()
                break
            accepted_this, interval = accept_proposal(pending)
            proposals += 1
            completed_blocks += 1
            if accepted_this:
                weights = list(proposal.weights)
                accepted += 1
            else:
                rejected += 1
            blocks_out.write(json.dumps({
                "seed_index": seed_index,
                "seed": seed,
                "method": method,
                "round": game_index,
                "family": family,
                "root_sha256": pending[0]["root_key"],
                "interval_proposal_minus_incumbent": list(interval),
                "accepted": accepted_this,
                "proposal_weights": proposal.weights,
                "incumbent_weights_after": weights,
                "all_four_slots_present": True,
            }, sort_keys=True, allow_nan=False) + "\n")
            blocks_out.flush()
            status = "NODE_BUDGET_REACHED"
        else:
            color = game_index % 2
            before = list(candidate.weights)
            row, query_rows, _end = play_episode(
                plan=plan, method=method, seed=seed, game_index=game_index,
                family=family, record=record, learner_color=color, candidate=candidate,
                foe=foe, variant=method, tree=learner if method == "TreeStrap" else None,
                td=learner if method == "TDLeaf" else None, arm_counts=counts,
                started=started, global_started=global_started, stop=stop,
            )
            games_out.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
            games_out.flush()
            for query in query_rows:
                queries_out.write(json.dumps(query, sort_keys=True, allow_nan=False) + "\n")
            queries_out.flush()
            games += 1
            planned_slots += 1
            if row["training_loss_mean"] is not None:
                loss_sum += row["training_loss_mean"] * row["training_loss_terms"]
                loss_terms += row["training_loss_terms"]
            if candidate.weights != before:
                counts["changed_episode_updates"] += 1
            status = "NODE_BUDGET_REACHED"
            if row["ending"] == "SEARCH_RESOURCE_UNKNOWN" and counts["candidate_nodes"] + counts["foe_nodes"] < plan["nodes_per_seed_method_arm"]:
                # Incomplete searches cannot produce an action; preserve the
                # censored episode and proceed to the next preassigned root.
                continue

    # Record every preassigned root/episode slot, even when a cap prevented
    # search. Missing endpoints stay censored rather than disappearing.
    started_games = games
    if method == "WDL":
        # Emit every remaining preassigned slot, including full unstarted blocks.
        for round_index, root_row in enumerate(rows):
            for slot_index, (variant, color) in enumerate(EPISODE_ORDER):
                if (round_index, slot_index) in recorded_wdl_slots:
                    continue
                reason = "UNSTARTED_AFTER_GLOBAL_TRAINING_CAP" if status == "GLOBAL_TRAINING_CAP_PARTIAL" else "UNSTARTED_AFTER_INCOMPLETE_PAIRED_BLOCK" if status == "INCOMPLETE_PAIRED_BLOCK_CENSORED" else "UNSTARTED_AFTER_ARM_NODE_CAP"
                placeholder = missing_slot(
                    method=method, seed_index=seed_index, seed=seed,
                    family=root_row["family"], game_index=round_index * 4 + slot_index,
                    variant=variant, learner_color=color, reason=reason,
                )
                games_out.write(json.dumps(placeholder, sort_keys=True, allow_nan=False) + "\n")
            games_out.flush()
        planned_slots = len(rows) * len(EPISODE_ORDER)
        missing_slots = planned_slots - games
    else:
        missing_slots = len(rows) - games
        if missing_slots > 0:
            reason = "UNSTARTED_AFTER_GLOBAL_TRAINING_CAP" if status == "GLOBAL_TRAINING_CAP_PARTIAL" else "UNSTARTED_AFTER_ARM_NODE_CAP"
            for root_row in rows[games:]:
                placeholder = missing_slot(
                    method=method, seed_index=seed_index, seed=seed,
                    family=root_row["family"], game_index=games,
                    variant=method, learner_color=games % 2, reason=reason,
                )
                games_out.write(json.dumps(placeholder, sort_keys=True, allow_nan=False) + "\n")
                games += 1
            games_out.flush()
        planned_slots = len(rows)
    total_nodes = counts["candidate_nodes"] + counts["foe_nodes"]
    if status == "GLOBAL_TRAINING_CAP_PARTIAL" or time.perf_counter() - global_started >= plan["training_hard_cap_seconds"]:
        status = "GLOBAL_TRAINING_CAP_PARTIAL"
    elif total_nodes == plan["nodes_per_seed_method_arm"] and method == "WDL" and status == "INCOMPLETE_PAIRED_BLOCK_CENSORED":
        status = "NODE_BUDGET_REACHED_WITH_CENSORED_BLOCK"
    elif method == "WDL" and status == "INCOMPLETE_PAIRED_BLOCK_CENSORED":
        pass
    elif total_nodes < plan["nodes_per_seed_method_arm"] and started_games >= (len(rows) * len(EPISODE_ORDER) if method == "WDL" else len(rows)):
        status = "ROOT_POOL_EXHAUSTED"
    result = {
        "seed_index": seed_index,
        "seed": seed,
        "method": method,
        "initial_weights": initial_weights(seed),
        "final_weights": list(weights if method == "WDL" else candidate.weights),
        "nodes_candidate": counts["candidate_nodes"],
        "nodes_fixed_foe": counts["foe_nodes"],
        "nodes_total": total_nodes,
        "searches": counts["searches"],
        "complete_searches": counts["complete_searches"],
        "incomplete_searches": counts["incomplete_searches"],
        "actual_terminal_games": counts["actual_terminal_games"],
        "unknown_games": counts["unknown_games"],
        "games_or_slots": planned_slots,
        "started_games": started_games,
        "planned_slots": planned_slots,
        "missing_slots": missing_slots,
        "training_loss_mean": loss_sum / loss_terms if loss_terms else None,
        "training_loss_terms": int(loss_terms),
        "tree_samples": counts["tree_samples"],
        "tree_active_samples": counts["tree_active_samples"],
        "td_observations": counts["td_observations"],
        "update_steps": counts["update_steps"],
        "wdl_proposal_blocks": completed_blocks,
        "wdl_proposals_accepted": accepted,
        "wdl_proposals_rejected": rejected,
        "wall_seconds": time.perf_counter() - started,
        "status": status,
        "reached_full_node_budget": total_nodes == plan["nodes_per_seed_method_arm"],
        "weights_are_strength_evidence": False,
    }
    return result


def run() -> dict:
    plan, registration, root_manifest = validate_registration()
    root_rows = root_manifest["roots"]
    stop = SharedDeleteStopReader(ROOT)
    stop()
    started = time.perf_counter()
    started_record = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "plan_sha256": sha((RUN / "plan.json").read_bytes()),
        "registration_sha256": sha((RUN / "registration.json").read_bytes()),
        "root_manifest_sha256": sha((RUN / "root-manifest.json").read_bytes()),
        "source_sha256": plan["source_sha256"],
        "session_id": plan["session_id"],
        "python_chess_version": chess.__version__,
    }
    with (RUN / "started.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(started_record, indent=2, sort_keys=True) + "\n")

    arms = []
    started_arm_count = 0
    status = "COMPLETE_TRAINING"
    with (RUN / "queries.jsonl").open("x", encoding="utf-8") as queries_out, (RUN / "games.jsonl").open("x", encoding="utf-8") as games_out, (RUN / "proposal-blocks.jsonl").open("x", encoding="utf-8") as blocks_out:
        for arm_index, (seed_index, method) in enumerate(plan["arm_order"]):
            seed = plan["seeds"][seed_index]
            stop()
            arm = _run_arm(plan, root_rows, seed_index, seed, method, started, stop, queries_out, games_out, blocks_out)
            arms.append(arm)
            started_arm_count += 1
            print(json.dumps(arm, sort_keys=True), flush=True)
            if arm["status"] == "GLOBAL_TRAINING_CAP_PARTIAL":
                status = "PARTIAL_TRAINING_CAP"
                for missing_seed_index, missing_method in plan["arm_order"][arm_index + 1:]:
                    missing_seed = plan["seeds"][missing_seed_index]
                    root_count = plan["roots_per_seed"]
                    slots_per_root = len(EPISODE_ORDER) if missing_method == "WDL" else 1
                    arms.append({
                        "seed_index": missing_seed_index,
                        "seed": missing_seed,
                        "method": missing_method,
                        "status": "NOT_STARTED_AFTER_TRAINING_CAP",
                        "nodes_candidate": 0,
                        "nodes_fixed_foe": 0,
                        "nodes_total": 0,
                        "started_games": 0,
                        "games_or_slots": root_count * slots_per_root,
                        "missing_slots": root_count * slots_per_root,
                        "training_loss_mean": None,
                        "training_loss_terms": 0,
                        "final_weights": None,
                    })
                break

    result = {
        "task": plan["task"],
        "status": status,
        "plan_sha256": sha((RUN / "plan.json").read_bytes()),
        "registration_sha256": sha((RUN / "registration.json").read_bytes()),
        "started_sha256": sha((RUN / "started.json").read_bytes()),
        "source_sha256": plan["source_sha256"],
        "root_manifest_sha256": sha((RUN / "root-manifest.json").read_bytes()),
        "wall_seconds": time.perf_counter() - started,
        "arm_count": len(arms),
        "started_arm_count": started_arm_count,
        "expected_arm_count": len(plan["arm_order"]),
        "nodes_total": sum(arm["nodes_total"] for arm in arms),
        "arms": arms,
        "evaluation_started": False,
        "eligible_for_evaluation": False,
        "interpretation": "Training outputs only; no evaluation, convergence, or strength conclusion. UNKNOWN/partial outcomes remain censored.",
    }
    complete_arms = len(arms) == len(plan["arm_order"]) and all(
        arm.get("status") in {"NODE_BUDGET_REACHED", "NODE_BUDGET_REACHED_WITH_CENSORED_BLOCK"}
        and arm.get("nodes_total") == plan["nodes_per_seed_method_arm"]
        for arm in arms
    )
    result["status"] = "COMPLETE_TRAINING" if complete_arms else "PARTIAL_TRAINING"
    result["eligible_for_evaluation"] = complete_arms
    with (RUN / "training-result.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, allow_nan=False))
