"""One-shot fixed-scale Generic TDLeaf training, bound to a frozen registration."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta, BudgetEnd
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv, unchanged_model, unchanged_learner
from results.dev_aux.task2622.freeze_study import initial_vector
from tools.local_agent.environment import require_identity

RUN = ROOT / "results/dev_aux/task2622/run"
RULES = (271001, 271002, 271003, 271004)
SEEDS = (1977, 8173, 27182, 31415)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate_plan_contract(plan: dict) -> None:
    training = plan["training"]
    search = plan["search"]
    initialization = plan["initialization"]["weights_by_rule_seed"]
    required_training = {"nodes_per_arm_candidate_plus_foe", "arms", "roots_per_rule", "H", "max_episodes_per_arm", "hard_seconds"}
    if not required_training.issubset(training):
        raise ValueError(f"registered training plan is missing fields: {sorted(required_training - set(training))}")
    if training["nodes_per_arm_candidate_plus_foe"] <= 0 or training["arms"] != len(RULES) * len(SEEDS):
        raise ValueError("registered training caps or arm count are invalid")
    if training["roots_per_rule"] <= 0 or training["H"] <= 0 or training["max_episodes_per_arm"] <= 0:
        raise ValueError("registered training traversal contract is invalid")
    if search["nodes_per_query"] <= 0 or search["depth"] <= 0:
        raise ValueError("registered search budget is invalid")
    if set(initialization) != {f"{rule}:{seed}" for rule in RULES for seed in SEEDS}:
        raise ValueError("registered initialization grid is incomplete")


def write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def validate_inputs():
    require_identity()
    plan_path = RUN / "plan.json"
    reg_path = RUN / "registration.json"
    pool_path = ROOT / "results/dev_aux/task2622/root-pools-v2.json"
    audit_path = ROOT / "results/dev_aux/task2622/root-pools-audit.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    validate_plan_contract(plan)
    if reg.get("state") != "REGISTERED_BEFORE_TRAINING_OR_EVALUATION":
        raise ValueError("no valid pre-run registration")
    if sha(plan_path.read_bytes()) != reg["plan_sha256"]:
        raise ValueError("plan hash mismatch")
    if sha(pool_path.read_bytes()) != reg["root_pools_sha256"]:
        raise ValueError("root pool hash mismatch")
    if sha(audit_path.read_bytes()) != reg["root_pools_audit_sha256"]:
        raise ValueError("root pool audit hash mismatch")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS_EXACT_HISTORY_SOURCE_HASH_REPLAY_FEATURE_AND_DISJOINTNESS_AUDIT":
        raise ValueError("root pool audit did not pass")
    for path, expected in reg["source_pins"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"source changed: {path}")
    session = json.loads((ROOT / ".local_agent/session.json").read_text(encoding="utf-8"))
    if session.get("state") != "active" or session.get("id") != reg["session_id"]:
        raise ValueError("registration session is not the current active session")
    if (RUN / "started.json").exists():
        raise FileExistsError("one-shot training already has a start receipt")
    if any((RUN / name).exists() for name in ("queries.jsonl", "episodes.jsonl", "training-result.json")):
        raise FileExistsError("one-shot training output exists; no retry/top-up")
    return plan, reg, json.loads(pool_path.read_text(encoding="utf-8"))


def run() -> dict:
    plan, reg, pools = validate_inputs()
    RUN.mkdir(parents=True, exist_ok=True)
    compiled = {}
    for rule in RULES:
        raw = (ROOT / f"results/dev_aux/task2525/rules-{rule}.json").read_bytes()
        compiled[rule] = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
    train_roots = {rule: [r for r in pools["training_roots"] if r["rule"] == rule] for rule in RULES}
    if any(len(rows) != plan["training"]["roots_per_rule"] for rows in train_roots.values()):
        raise ValueError("registered training root count mismatch")

    stop = SharedDeleteStopReader(ROOT)
    began = time.perf_counter()
    write_once(RUN / "started.json", {"at_monotonic_origin": time.perf_counter(),
        "plan_sha256": reg["plan_sha256"], "registration_sha256": sha((RUN / "registration.json").read_bytes()),
        "session_id": reg["session_id"], "root_pools_sha256": reg["root_pools_sha256"]})
    arms, arm_results = [], []
    status = "COMPLETE"
    with (RUN / "queries.jsonl").open("x", encoding="utf-8") as qout, \
         (RUN / "episodes.jsonl").open("x", encoding="utf-8") as eout:
        for rule in RULES:
            panel = train_roots[rule]
            dimension = len(panel[0]["channels"])
            for seed in SEEDS:
                stop()
                initial = initial_vector(seed, dimension)
                expected_initial = plan["initialization"]["weights_by_rule_seed"][f"{rule}:{seed}"]
                if initial != expected_initial:
                    raise ValueError(f"rule {rule}, seed {seed}: initial weights differ from frozen vector")
                model = unchanged_model(initial)
                foe = unchanged_model([1.0] * dimension)
                td = unchanged_learner()
                arm_began = time.perf_counter()
                counts = Counter()
                max_games = plan["training"]["max_episodes_per_arm"]
                for game in range(max_games):
                    if counts["nodes"] >= plan["training"]["nodes_per_arm_candidate_plus_foe"]:
                        break
                    if time.perf_counter() - began >= plan["training"]["hard_seconds"]:
                        status = "PARTIAL_GLOBAL_TIME_CAP"
                        break
                    root = panel[game % len(panel)]
                    learner_color = game % 2
                    env = FixedScaleSessionEnv(GameSession.replay(compiled[rule],
                        deserialize_game_record(json.dumps(root["record"]))))
                    if env.record() != root["record"]:
                        raise ValueError("registered training root failed exact replay")
                    before_episode = env.record()
                    episode_start_nodes = counts["nodes"]
                    ended = "HORIZON_UNKNOWN"
                    episode_queries = 0
                    for ply in range(plan["training"]["H"]):
                        stop()
                        try:
                            actual = env.terminal()
                        except NonScoringTerminal:
                            ended = "NON_SCORING_UNKNOWN"
                            break
                        if actual is not None:
                            ended = "ACTUAL_TERMINAL"
                            break
                        remaining = plan["training"]["nodes_per_arm_candidate_plus_foe"] - counts["nodes"]
                        wall = plan["training"]["hard_seconds"] - (time.perf_counter() - began)
                        if remaining <= 0:
                            ended = "NODE_CAP_UNKNOWN"
                            break
                        if wall <= 0:
                            status = "PARTIAL_GLOBAL_TIME_CAP"
                            ended = "TIME_CAP_UNKNOWN"
                            break
                        actor = env.player()
                        learner_turn = actor == learner_color
                        current = model if learner_turn else foe
                        record_before = env.record()
                        state_before = env.session.state
                        remaining_run = plan["training"]["hard_seconds"] - (time.perf_counter() - began)
                        request = min(plan["search"]["nodes_per_query"], remaining)
                        receipt = AlphaBeta(plan["search"]["depth"], 0).search(
                            env, current, nodes=request,
                            seconds=min(plan["search"]["seconds_per_query"], max(1e-6, remaining_run)),
                            seed=plan["search"]["ordering_seed_base"] + rule * 1_000_000 + seed * 1000 + game * 128 + ply,
                            cancel=stop)
                        if env.record() != record_before or env.session.state != state_before:
                            raise AssertionError("search mutated the complete GameSession history")
                        counts["nodes"] += receipt.nodes
                        counts["candidate_nodes" if learner_turn else "foe_nodes"] += receipt.nodes
                        counts["queries"] += 1
                        episode_queries += 1
                        if receipt.complete:
                            if learner_turn:
                                td.observe(model, receipt)
                            env.push(receipt.action)
                        row = {"rule": rule, "seed": seed, "episode": game, "root_family": root["family"],
                               "learner_color": learner_color, "ply": ply, "actor": actor,
                               "learner_turn": learner_turn, "weights_before_search": list(current.weights),
                               "record_before": record_before, "record_after": env.record(),
                               "complete": receipt.complete, "value": receipt.value,
                               "pv_phi": receipt.pv_phi, "pv_terminal": receipt.pv_terminal,
                               "nodes": receipt.nodes, "requested_nodes": request,
                               "seconds": receipt.seconds, "search_reason": receipt.reason}
                        qout.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                        qout.flush()
                        if not receipt.complete:
                            ended = "SEARCH_RESOURCE_UNKNOWN"
                            counts["incomplete_searches"] += 1
                            break
                        env.replay()
                    try:
                        actual = env.terminal()
                    except NonScoringTerminal:
                        actual, ended = None, "NON_SCORING_UNKNOWN"
                    if actual is not None:
                        ended = "ACTUAL_TERMINAL"
                        counts["actual_terminal"] += 1
                    else:
                        counts["UNKNOWN"] += 1
                    stats = td.finish(model, actual)
                    counts["episodes"] += 1
                    counts["nonzero_updates"] += bool(stats["changed"])
                    episode = {"rule": rule, "seed": seed, "episode": game,
                               "root_family": root["family"], "learner_color": learner_color,
                               "initial_weights": initial, "final_weights": list(model.weights),
                               "start_record": before_episode, "final_record": env.record(),
                               "actual_outcome": actual, "ending": ended,
                               "nodes": counts["nodes"] - episode_start_nodes,
                               "queries": episode_queries, "stats": stats}
                    eout.write(json.dumps(episode, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
                    eout.flush()
                    if counts["nodes"] > plan["training"]["nodes_per_arm_candidate_plus_foe"]:
                        raise AssertionError("arm exceeded its combined candidate-plus-foe node cap")
                    if status != "COMPLETE":
                        break
                arm = {"rule": rule, "seed": seed, "initial_weights": initial,
                       "final_weights": list(model.weights), "nodes": counts["nodes"],
                       "seconds": time.perf_counter() - arm_began, "counts": dict(counts),
                       "status": "NODE_CAP" if counts["nodes"] == plan["training"]["nodes_per_arm_candidate_plus_foe"] else "INCOMPLETE"}
                if model.fixed != 0 or model.scale != 10.0 or model.weights[0] != 1.0:
                    raise AssertionError("training changed the fixed material-scale coordinate")
                arms.append(arm)
                if arm["status"] != "NODE_CAP":
                    status = "PARTIAL_ARM"
                if status != "COMPLETE":
                    break
            if status != "COMPLETE":
                break
    expected_arms = plan["training"]["arms"]
    if len(arms) == expected_arms:
        expected_keys = {(rule, seed) for rule in RULES for seed in SEEDS}
        if {(arm["rule"], arm["seed"]) for arm in arms} != expected_keys:
            raise AssertionError("training arm set differs from frozen rule/seed grid")
    result = {"status": status if status != "COMPLETE" or len(arms) == expected_arms else "PARTIAL_ARM",
              "expected_arms": expected_arms, "arms": arms,
              "nodes": sum(a["nodes"] for a in arms), "episodes": sum(a["counts"]["episodes"] for a in arms),
              "actual_terminal": sum(a["counts"].get("actual_terminal", 0) for a in arms),
              "UNKNOWN": sum(a["counts"].get("UNKNOWN", 0) for a in arms),
              "queries": sum(a["counts"].get("queries", 0) for a in arms),
              "seconds": time.perf_counter() - began,
              "plan_sha256": reg["plan_sha256"], "registration_sha256": sha((RUN / "registration.json").read_bytes()),
              "root_pools_sha256": reg["root_pools_sha256"],
              "scope": "Fixed-scale SAME TDLeaf training feasibility/comparison; four existing development rules only."}
    write_once(RUN / "training-result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "arms"}, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    run()
