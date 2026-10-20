"""Independent full replay and accounting audit for task2620 run-002.

This audit reads immutable plan/source pins and append-only evaluation logs. It
never launches or modifies an evaluation, and writes its result once.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import chess
from results.dev_aux.task2565.train import restore
from results.dev_aux.task2620.protocol import validate_plan
from results.dev_aux.task2618.analyze_learners import (
    finite_panel_analysis,
    validate_evaluation_accounting,
)
from results.dev_aux.task2618.evaluate_learners import (
    finite_reward_bounds,
    learner_reward,
    verify_training_result,
)
from tools.local_agent.environment import require_identity

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/dev_aux/task2620/run-002"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise ValueError(f"invalid JSONL at {path.name}:{number}") from exc


def verify_query_stream(plan, slots, root_by_family, arms, initial_by_seed, query_path):
    """Replay a byte-stable saved prefix or closed stream, without final-result claims."""
    foe_weights = plan["fixed_foe_weights"]
    caps = plan["evaluation"]["caps_by_family"]
    per_search_cap = plan["evaluation"]["nodes_per_search"]
    query_seconds_cap = plan["evaluation"]["seconds_per_search"]
    per_slot = defaultdict(lambda: {"nodes": 0, "queries": 0,
                                    "last_record": None, "last_complete": None,
                                    "ply": 0, "seen": False})
    query_count = 0
    last_slot_index = -1
    current_index = None
    env = None

    for q in read_jsonl(query_path):
        query_count += 1
        index = q.get("slot_index")
        if not isinstance(index, int) or not 0 <= index < len(slots):
            raise ValueError("query has invalid slot index")
        if index < last_slot_index:
            raise ValueError("query slots are not in frozen execution order")
        expected_slot = slots[index]
        if tuple(q.get("slot", ())) != expected_slot:
            raise ValueError(f"query {query_count} is not bound to its frozen slot")
        seed_index, seed, family, learner_color, endpoint = expected_slot
        if tuple(q.get("slot")) != (seed_index, seed, family, learner_color, endpoint):
            raise ValueError("query identity mismatch")
        if current_index != index:
            current_index = index
            last_slot_index = index
            env = restore(0, None, root_by_family[family])
            if env.record() != root_by_family[family] or env.terminal() is not None:
                raise ValueError(f"invalid/nonterminal replay root {family}")
        acc = per_slot[index]
        if acc["seen"] and acc["last_complete"] is False:
            raise ValueError(f"slot {index} continued after an incomplete search")
        if q.get("ply") != acc["ply"]:
            raise ValueError(f"slot {index} query ply is not contiguous")
        actor = env.player()
        if actor != q.get("actor") or q.get("learner_color") != learner_color:
            raise ValueError(f"slot {index} actor/color mismatch")
        if q.get("endpoint") != endpoint:
            raise ValueError(f"slot {index} endpoint mismatch")
        if env.terminal() is not None:
            raise ValueError(f"slot {index} searched an already-terminal state")
        before = env.record()
        if q.get("record_before") != before:
            raise ValueError(f"slot {index} pre-search history mismatch")
        family_cap = caps[str(family)]
        if q.get("family_cap_nodes_both_sides") != family_cap:
            raise ValueError(f"slot {index} cap does not match registration")
        remaining_slot = family_cap - acc["nodes"]
        if remaining_slot <= 0:
            raise ValueError(f"slot {index} queried after its node cap")
        expected_request = min(per_search_cap, remaining_slot)
        if q.get("effective_nodes") != expected_request:
            raise ValueError(f"slot {index} effective search request is wrong")
        effective_seconds = q.get("effective_seconds")
        if not isinstance(effective_seconds, (int, float)) or not 0 < effective_seconds <= query_seconds_cap:
            raise ValueError(f"slot {index} per-search time request exceeds its cap")
        nodes = q.get("nodes")
        seconds = q.get("seconds")
        if type(nodes) is not int or not 0 <= nodes <= expected_request:
            raise ValueError(f"slot {index} node receipt exceeds its request")
        if not isinstance(seconds, (int, float)) or seconds < 0 or seconds > effective_seconds + 0.05:
            raise ValueError(f"slot {index} time receipt exceeds its request")
        if q.get("ordering_seed") != (plan["evaluation"]["ordering_seed_base"]
                + seed * 1_000_000 + family * 1_000 + q["ply"]):
            raise ValueError(f"slot {index} ordering seed mismatch")
        arm = None if endpoint == "initial" else arms[(seed_index, endpoint)]
        expected_weights = (initial_by_seed[seed] if endpoint == "initial" else arm["final_weights"])
        actor_weights = expected_weights if actor == learner_color else foe_weights
        if q.get("weights") != actor_weights:
            raise ValueError(f"slot {index} searched with the wrong actor weights")
        complete = q.get("complete")
        if type(complete) is not bool:
            raise ValueError(f"slot {index} complete flag is not boolean")
        action = q.get("action")
        if complete:
            if not isinstance(action, str):
                raise ValueError(f"slot {index} complete search lacks an action")
            move = chess.Move.from_uci(action)
            if move not in env.board.legal_moves:
                raise ValueError(f"slot {index} returned illegal Chess move {action}")
            env.push(move)
        elif action is not None:
            raise ValueError(f"slot {index} incomplete search exposed an action")
        after = env.record()
        if q.get("record_after") != after:
            raise ValueError(f"slot {index} post-search/action history mismatch")
        acc["nodes"] += nodes
        acc["queries"] += 1
        acc["ply"] += 1
        acc["last_record"] = after
        acc["last_complete"] = complete
        acc["seen"] = True
        if q.get("total_slot_nodes_both_sides") != acc["nodes"]:
            raise ValueError(f"slot {index} cumulative both-side nodes mismatch")
        if acc["nodes"] > family_cap:
            raise ValueError(f"slot {index} exceeded family node cap")

    return per_slot, query_count


def audit() -> dict:
    require_identity()
    output = RUN / "independent-audit.json"
    if output.exists():
        raise FileExistsError("independent audit is write-once")
    required = ("plan.json", "registration.json", "training-result.json",
                "evaluation-root-manifest.json", "evaluation-started.json",
                "evaluation-result.json", "evaluation-games.jsonl",
                "evaluation-queries.jsonl", "launch-exit.json")
    missing = [name for name in required if not (RUN / name).is_file()]
    if missing:
        raise FileNotFoundError("run is not closed; missing " + ", ".join(missing))

    plan_raw = (RUN / "plan.json").read_bytes()
    plan = json.loads(plan_raw)
    validate_plan(plan)
    if chess.__version__ != plan["python_chess_version"]:
        raise ValueError("Python Chess runtime version differs from the frozen plan")
    reg_raw = (RUN / "registration.json").read_bytes()
    registration = json.loads(reg_raw)
    if registration.get("status") != "REGISTERED_PRE_EVALUATION":
        raise ValueError("registration is not the expected pre-evaluation state")
    if registration.get("plan_sha256") != sha(plan_raw):
        raise ValueError("registration does not bind exact plan")
    if registration.get("training_result_sha256") != plan.get("training_result_sha256"):
        raise ValueError("registration and plan bind different training receipts")
    if registration.get("source_sha256") != plan.get("source_sha256"):
        raise ValueError("registration and plan bind different source pins")
    for relative, expected in plan["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != expected:
            raise ValueError(f"pinned source changed: {relative}")
    launch_claim = read_json(RUN / "launch-claim.json")
    launch_started = read_json(RUN / "launch-started.json")
    evaluation_started = read_json(RUN / "evaluation-started.json")
    if evaluation_started.get("plan_sha256") != sha(plan_raw):
        raise ValueError("evaluation start does not bind exact plan")
    if evaluation_started.get("registration_sha256") != sha(reg_raw):
        raise ValueError("evaluation start does not bind registration")
    if evaluation_started.get("source_sha256") != plan.get("source_sha256"):
        raise ValueError("evaluation start does not bind registered sources")
    if (evaluation_started.get("registration_session_id") != plan.get("session_id")
            or evaluation_started.get("launch_session_id") != plan.get("session_id")):
        raise ValueError("evaluation registration/launch session identity mismatch")
    if launch_started.get("pid") != launch_claim.get("pid") and launch_claim.get("pid") is not None:
        raise ValueError("launcher claim and process-start PID disagree")
    if launch_started.get("command") != launch_claim.get("command"):
        raise ValueError("launcher claim and process-start command disagree")
    training_raw = (RUN / "training-result.json").read_bytes()
    if sha(training_raw) != plan["training_result_sha256"]:
        raise ValueError("training result hash mismatch")
    training_plan_raw = (ROOT / plan["training_plan_path"]).read_bytes()
    arms = verify_training_result(json.loads(training_plan_raw),
                                  json.loads(training_raw),
                                  sha(training_plan_raw))
    roots_raw = (RUN / "evaluation-root-manifest.json").read_bytes()
    if sha(roots_raw) != plan["evaluation_root_manifest_sha256"]:
        raise ValueError("root manifest hash mismatch")
    roots_doc = json.loads(roots_raw)
    root_by_family = {row["family"]: row["record"] for row in roots_doc["roots"]}
    if len(root_by_family) != len(roots_doc["roots"]) or len(root_by_family) != plan["evaluation"]["root_count"]:
        raise ValueError("root manifest has duplicate or missing families")
    slots = [tuple(row) for row in plan["evaluation"]["ordered_slots"]]
    if len(slots) != plan["evaluation"]["expected_slots"] or len(set(slots)) != len(slots):
        raise ValueError("frozen slots are incomplete or duplicated")
    if set(root_by_family) != set(map(int, plan["evaluation"]["caps_by_family"])):
        raise ValueError("root and cap manifests differ")
    initial_by_seed = {int(arm["seed"]): arm["initial_weights"]
                       for arm in json.loads(training_raw)["arms"]}
    caps = plan["evaluation"]["caps_by_family"]
    per_slot, query_count = verify_query_stream(
        plan, slots, root_by_family, arms, initial_by_seed, RUN / "evaluation-queries.jsonl")

    games = list(read_jsonl(RUN / "evaluation-games.jsonl"))
    game_by_index = {}
    counts = Counter()
    endpoint_outcomes = defaultdict(Counter)
    seed_endpoint_outcomes = defaultdict(Counter)
    previous_game_index = -1
    for row in games:
        index = row.get("slot_index")
        if (not isinstance(index, int) or not 0 <= index < len(slots)
                or index in game_by_index or index <= previous_game_index):
            raise ValueError("duplicate, unordered or invalid game slot index")
        previous_game_index = index
        slot = slots[index]
        if tuple(row.get("slot", ())) != slot:
            raise ValueError(f"game {index} differs from frozen slot")
        si, seed, family, color, endpoint = slot
        if (row.get("seed_index"), row.get("seed"), row.get("family"),
                row.get("learner_color"), row.get("endpoint")) != slot:
            raise ValueError(f"game {index} identity fields disagree")
        acc = per_slot[index]
        root = root_by_family[family]
        if row.get("initial_record") != root:
            raise ValueError(f"game {index} initial history mismatch")
        if acc["seen"]:
            if acc["last_record"] != row.get("final_record"):
                raise ValueError(f"game {index} final state differs from audited actions")
        elif row.get("final_record") != root:
            raise ValueError(f"game {index} has an unlogged action")
        final = row["final_record"]
        replay = restore(0, None, final)
        outcome = replay.terminal()
        if row.get("outcome_white_relative") != outcome:
            raise ValueError(f"game {index} outcome is not actual terminal Chess result")
        if row.get("ending") == "ACTUAL_TERMINAL" and outcome is None:
            raise ValueError(f"game {index} claims terminal without a rule result")
        if outcome is not None and row.get("ending") != "ACTUAL_TERMINAL":
            raise ValueError(f"game {index} omits an available terminal result")
        if row.get("nodes") != acc["nodes"] or row.get("searches") != acc["queries"]:
            raise ValueError(f"game {index} node/query totals disagree with search receipts")
        if row.get("family_cap_nodes_both_sides") != caps[str(family)]:
            raise ValueError(f"game {index} cap mismatch")
        if row.get("weights") != (initial_by_seed[seed] if endpoint == "initial"
                                   else arms[(si, endpoint)]["final_weights"]):
            raise ValueError(f"game {index} endpoint weights mismatch")
        if row.get("learner_reward") != learner_reward(outcome, color):
            raise ValueError(f"game {index} learner reward mismatch")
        if row.get("reward_bounds") != list(finite_reward_bounds(outcome, color)):
            raise ValueError(f"game {index} reward bounds mismatch")
        ending = row.get("ending")
        slot_queries = acc["queries"]
        if ending == "SEARCH_RESOURCE_UNKNOWN":
            # A final incomplete receipt is the sole admissible cause of this label.
            if not slot_queries or acc["last_complete"] is not False:
                raise ValueError(f"game {index} has no final incomplete search receipt")
        elif ending == "HORIZON_UNKNOWN":
            if slot_queries != plan["evaluation"]["max_plies_per_game"] or acc["last_complete"] is not True:
                raise ValueError(f"game {index} horizon UNKNOWN ended at the wrong ply")
        elif ending == "SLOT_NODE_CAP_UNKNOWN":
            if acc["nodes"] != caps[str(family)] or acc["last_complete"] is not True:
                raise ValueError(f"game {index} node-cap UNKNOWN has inconsistent search receipts")
        elif ending == "GLOBAL_CAP_UNKNOWN":
            if acc["seen"] and acc["last_complete"] is not True:
                raise ValueError(f"game {index} global-cap UNKNOWN follows an incomplete search")
        elif ending != "ACTUAL_TERMINAL":
            raise ValueError(f"game {index} has unrecognized ending reason {ending!r}")
        if row.get("unknown_is_draw") is not False:
            raise ValueError(f"game {index} converted UNKNOWN to draw")
        game_by_index[index] = row
        counts["actual_terminal" if outcome is not None else "unknown"] += 1
        counts[f"ending:{row['ending']}"] += 1
        counts[f"outcome:{outcome}"] += 1
        outcome_key = "UNKNOWN" if outcome is None else str(outcome)
        endpoint_outcomes[endpoint][outcome_key] += 1
        seed_endpoint_outcomes[(seed, endpoint)][outcome_key] += 1

    game_indices = set(game_by_index)
    if any(index not in game_indices for index, acc in per_slot.items() if acc["seen"]):
        raise ValueError("query stream includes a slot without a game receipt")
    eval_result = read_json(RUN / "evaluation-result.json")
    validate_evaluation_accounting(plan, eval_result, games)
    if eval_result.get("training_result_sha256") != sha(training_raw):
        raise ValueError("evaluation result training receipt hash mismatch")
    if eval_result.get("plan_sha256") != sha(plan_raw):
        raise ValueError("evaluation result plan hash mismatch")
    if eval_result.get("status") not in {"COMPLETE", "PARTIAL_GLOBAL_CAP"}:
        raise ValueError("unrecognized final evaluation status")
    if any(row.get("ending") == "GLOBAL_CAP_UNKNOWN" for row in games):
        if eval_result.get("status") != "PARTIAL_GLOBAL_CAP":
            raise ValueError("game reports global-cap exhaustion but evaluation is not partial")
    if eval_result.get("queries") != query_count:
        raise ValueError("result query total disagrees with full query stream")
    if eval_result.get("nodes") != sum(acc["nodes"] for acc in per_slot.values()):
        raise ValueError("result node total disagrees with query stream")
    missing_slots = sorted(set(range(len(slots))) - set(game_by_index))
    endpoint_missing = Counter(slots[i][4] for i in missing_slots)
    seed_endpoint_missing = Counter((slots[i][1], slots[i][4]) for i in missing_slots)
    missing_queries_for_games = [i for i in game_by_index if not per_slot[i]["seen"]]
    if missing_queries_for_games:
        raise ValueError("game receipts lack their corresponding query history")
    panel = finite_panel_analysis(plan, games)
    launcher = read_json(RUN / "launch-exit.json")
    if launcher.get("return_code") != 0:
        raise ValueError("one-shot launcher did not exit successfully")
    if launcher.get("wall_seconds", 0) > plan["evaluation"]["hard_cap_seconds"] + 1:
        raise ValueError("launcher wall time exceeded the frozen evaluation cap")
    if eval_result.get("seconds", 0) > plan["evaluation"]["hard_cap_seconds"] + 1:
        raise ValueError("evaluation-reported time exceeded the frozen cap")
    from datetime import datetime
    began = datetime.fromisoformat(launch_started["utc"])
    ended = datetime.fromisoformat(launcher["utc"])
    preparation = datetime.fromisoformat(plan["preparation_started_at"])
    if (ended - began).total_seconds() > launcher.get("wall_seconds", 0) + 2:
        raise ValueError("launcher timestamps conflict with measured wall time")
    if (ended - preparation).total_seconds() > plan["all_in_hard_cap_seconds"] + 2:
        raise ValueError("actual all-in elapsed time exceeded its frozen cap")
    training_document = json.loads(training_raw)
    training_metrics = [{
        "seed_index": arm["seed_index"], "seed": arm["seed"], "method": arm["method"],
        "status": arm["status"], "training_loss_mean": arm["training_loss_mean"],
        "training_loss_terms": arm["training_loss_terms"], "tree_samples": arm["tree_samples"],
        "tree_active_samples": arm["tree_active_samples"], "td_observations": arm["td_observations"],
        "update_steps": arm["update_steps"], "actual_terminal_games": arm["actual_terminal_games"],
        "unknown_games": arm["unknown_games"], "missing_slots": arm["missing_slots"],
        "nodes_total": arm["nodes_total"], "weights_are_strength_evidence": arm["weights_are_strength_evidence"],
    } for arm in sorted(training_document["arms"], key=lambda row: (row["seed_index"], row["method"]))]
    result = {
        "status": "PASS",
        "task": plan["task"],
        "registered_slots": len(slots),
        "game_receipts": len(games),
        "missing_slots": missing_slots,
        "query_receipts": query_count,
        "actual_terminal": counts["actual_terminal"],
        "unknown": counts["unknown"],
        "outcomes_white_relative": {str(k): v for k, v in sorted(
            ((key[8:], value) for key, value in counts.items() if key.startswith("outcome:")))},
        "ending_counts": {k[7:]: v for k, v in sorted(counts.items()) if k.startswith("ending:")},
        "outcome_counts_by_endpoint": {
            endpoint: {key: endpoint_outcomes[endpoint][key] for key in ("-1", "0", "1", "UNKNOWN")}
            for endpoint in ("initial", "TreeStrap", "TDLeaf", "WDL")},
        "outcome_counts_by_seed_endpoint": {
            f"{seed}:{endpoint}": {
                key: seed_endpoint_outcomes[(seed, endpoint)][key] for key in ("-1", "0", "1", "UNKNOWN")
            }
            for seed in sorted(plan["seeds"])
            for endpoint in ("initial", "TreeStrap", "TDLeaf", "WDL")},
        "missing_by_endpoint": {endpoint: endpoint_missing[endpoint]
                                 for endpoint in ("initial", "TreeStrap", "TDLeaf", "WDL")},
        "missing_by_seed_endpoint": {
            f"{seed}:{endpoint}": seed_endpoint_missing[(seed, endpoint)]
            for seed in sorted(plan["seeds"])
            for endpoint in ("initial", "TreeStrap", "TDLeaf", "WDL")},
        "node_total": eval_result["nodes"],
        "all_registered_slots_accounted_for": len(games) + len(missing_slots) == len(slots),
        "unknown_and_missing_are_full_panel_bounds": True,
        "full_rule_action_replay": "PASS",
        "both_sides_node_and_search_accounting": "PASS",
        "plan_sha256": sha(plan_raw),
        "registration_sha256": sha(reg_raw),
        "evaluation_result_sha256": sha((RUN / "evaluation-result.json").read_bytes()),
        "evaluation_games_sha256": sha((RUN / "evaluation-games.jsonl").read_bytes()),
        "evaluation_queries_sha256": sha((RUN / "evaluation-queries.jsonl").read_bytes()),
        "training_result_sha256": sha(training_raw),
        "launcher_exit": launcher,
        "training_metrics_all_seed_arms": training_metrics,
        "finite_panel_contrasts": panel["contrasts"],
        "limitations": [
            "Finite 48-start panel against one fixed foe; not a population confidence interval.",
            "Exact starting-history disjointness does not prove descendant/transposition independence.",
            "All UNKNOWN and missing outcomes retain [-1,+1] bounds; no draw or sample deletion.",
        ],
    }
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True, allow_nan=False))
