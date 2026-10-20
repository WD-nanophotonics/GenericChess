"""Descriptive feature/action exposure after the registered audits pass."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
RUN = ROOT / "results/dev_aux/task2628/run"
OUT = RUN / "feature-exposure.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_channels(phi: list[float], names: list[tuple[str, str]]) -> list[str]:
    if len(phi) != len(names):
        raise ValueError("feature vector dimension differs from declared channels")
    # Coordinate zero is the fixed board-unit scale, not a learned channel.
    return [f"{kind}:{type_id}" for index, ((kind, type_id), value) in enumerate(zip(names, phi))
            if index > 0 and value != 0]


def added_patterns(start: dict, final: dict) -> Counter[str]:
    before = start["actions"]
    after = final["actions"]
    if after[:len(before)] != before:
        raise ValueError("final game record does not preserve its full starting history")
    return Counter(action["pattern_id"] for action in after[len(before):])


def read_rows(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def analyze() -> dict:
    if OUT.exists():
        raise FileExistsError("feature-exposure analysis is write-once")
    training_audit_path = RUN / "training-audit.json"
    evaluation_audit_path = RUN / "evaluation-audit.json"
    training_result_path = RUN / "training-result.json"
    registration_path = RUN / "registration.json"
    started_path = RUN / "started.json"
    plan_path = RUN / "plan.json"
    pool_audit_path = ROOT / "results/dev_aux/task2627/rule15-successor-pool-audit.json"
    training_audit = json.loads(training_audit_path.read_text(encoding="utf-8"))
    training_result = json.loads(training_result_path.read_text(encoding="utf-8"))
    reg = json.loads(registration_path.read_text(encoding="utf-8"))
    started = json.loads(started_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pool_audit = json.loads(pool_audit_path.read_text(encoding="utf-8"))
    evaluation_audit = json.loads(evaluation_audit_path.read_text(encoding="utf-8"))
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    if training_audit.get("status") != "PASS_FULL_HISTORY_ACTUAL_TERMINAL_NODE_CAP_AND_TD_UPDATE_REPLAY":
        raise ValueError("full-history training audit must pass before exposure analysis")
    if training_result.get("status") != "COMPLETE" or sha(training_result_path) != training_audit.get("training_result_sha256"):
        raise ValueError("exposure analysis requires the audited complete registered training result")
    if evaluation_audit.get("status") != "PASS_REGISTERED_SLOT_ACTUAL_TERMINAL_HISTORY_AND_CAP_AUDIT":
        raise ValueError("full-history evaluation audit must pass before exposure analysis")
    if (sha(plan_path) != reg["plan_sha256"]
            or started.get("registration_sha256") != sha(registration_path)
            or started.get("plan_sha256") != reg["plan_sha256"]):
        raise ValueError("study registration or plan hash mismatch")
    if pool_audit.get("status") != "PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT":
        raise ValueError("source-bound root panel audit is required")
    if (sha(pool_path) != reg["root_pools_sha256"]
            or sha(pool_audit_path) != reg["root_pools_audit_sha256"]):
        raise ValueError("registered source-bound root pool or its audit changed")

    seeds = set(plan["seeds"])
    query_counts = {seed: Counter() for seed in seeds}
    active = {seed: Counter() for seed in seeds}
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    rules = {rule: json.loads((ROOT / f"results/dev_aux/task2433/rules-{rule}.json").read_text(encoding="utf-8"))
             for rule in plan["domain"]["rules"]}
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    channels = {}
    for rule, raw in rules.items():
        compiled = compile_ruleset_for_execution(ruleset_from_dict(raw))
        root = next(row for row in pool["training_roots"] if row["rule_index"] == rule)
        env = FixedScaleSessionEnv(GameSession.replay(compiled,
            deserialize_game_record(json.dumps(root["record"]))))
        channels[rule] = env.names

    total_queries = 0
    for row in read_rows(RUN / "queries.jsonl"):
        total_queries += 1
        seed, rule = row["seed"], row["rule"]
        if seed not in seeds or rule not in channels:
            raise ValueError("unregistered rule or seed in training query stream")
        if not row["learner_turn"]:
            continue
        counts = query_counts[seed]
        counts["candidate_queries"] += 1
        if not row["complete"]:
            counts["incomplete_candidate_queries"] += 1
            continue
        counts["complete_candidate_queries"] += 1
        if row["pv_terminal"]:
            counts["terminal_pv_zero_gradient"] += 1
            continue
        for name in active_channels(row["pv_phi"], channels[rule]):
            active[seed][name] += 1

    action_counts = Counter()
    episodes = 0
    for row in read_rows(RUN / "episodes.jsonl"):
        if row["seed"] not in seeds or row["rule"] not in channels:
            raise ValueError("unregistered rule or seed in training episode stream")
        episodes += 1
        action_counts.update(added_patterns(row["start_record"], row["final_record"]))
    if episodes != training_result["episodes"]:
        raise ValueError("episode exposure count differs from audited training receipt")
    if total_queries != training_result["queries"]:
        raise ValueError("query exposure count differs from audited training receipt")

    endpoints = Counter()
    for row in read_rows(RUN / "eval-games.jsonl"):
        endpoints.update({f"{row['slot'][4]}:{key}": value
                          for key, value in added_patterns(row["initial_record"], row["final_record"]).items()})

    result = {
        "status": "PASS_DESCRIPTIVE_FEATURE_AND_ACTION_EXPOSURE",
        "plan_sha256": sha(plan_path), "registration_sha256": sha(registration_path),
        "started_receipt_sha256": sha(started_path),
        "training_result_sha256": sha(training_result_path),
        "training_audit_sha256": sha(training_audit_path),
        "evaluation_audit_sha256": sha(evaluation_audit_path),
        "training_queries_sha256": sha(RUN / "queries.jsonl"),
        "training_episodes_sha256": sha(RUN / "episodes.jsonl"),
        "feature_exposures_by_seed": {str(seed): dict(active[seed]) for seed in sorted(seeds)},
        "candidate_query_counts_by_seed": {str(seed): dict(query_counts[seed]) for seed in sorted(seeds)},
        "executed_action_patterns_after_training_roots": dict(action_counts),
        "training_episodes": episodes,
        "evaluation_action_patterns_by_endpoint": dict(endpoints),
        "scope": "Descriptive exposure only; nonzero PV features and executed action patterns do not establish causal feature value or broad Generic transfer.",
        "source_note": "Supplemental post-audit diagnostic; does not change or re-execute the registered learner/evaluator.",
    }
    with OUT.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    analyze()
