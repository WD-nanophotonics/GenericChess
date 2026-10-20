"""Reconstruct the missing post-run summary from the single completed log set."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
RUN = ROOT / "results/dev_aux/task2628/run"
OUT = RUN / "training-result-recovered.json"
REPORT = RUN / "training-recovery.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed JSONL at {path}:{number}") from exc


def main() -> dict:
    if OUT.exists() or REPORT.exists():
        raise FileExistsError("training recovery is write-once")
    canonical = RUN / "training-result.json"
    if canonical.exists():
        raise FileExistsError("canonical training result already exists")
    plan_path, reg_path = RUN / "plan.json", RUN / "registration.json"
    exit_path, start_path = RUN / "launch-exit.json", RUN / "launch-started.json"
    stdout_path = RUN / "launcher.stdout"
    stderr_path = RUN / "launcher.stderr"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    exit_receipt = json.loads(exit_path.read_text(encoding="utf-8"))
    start_receipt = json.loads(start_path.read_text(encoding="utf-8"))
    error_text = stderr_path.read_text(encoding="utf-8")
    if exit_receipt.get("status") != "EXIT_RECORDED" or exit_receipt.get("return_code") != 1:
        raise ValueError("recovery requires the preserved failed launcher receipt")
    if "KeyError: 'rule_index'" not in error_text or "train.py\", line 246" not in error_text:
        raise ValueError("launcher failure does not match the known post-run summary-key defect")
    if sha(stderr_path) != exit_receipt.get("stderr_sha256"):
        raise ValueError("stderr differs from the launch exit receipt")
    if sha(stdout_path) != exit_receipt.get("stdout_sha256"):
        raise ValueError("stdout differs from the launch exit receipt")
    if sha(plan_path) != reg.get("plan_sha256") or exit_receipt.get("plan_sha256") != reg.get("plan_sha256"):
        raise ValueError("frozen plan hash mismatch")
    if sha(reg_path) != start_receipt.get("registration_sha256"):
        raise ValueError("registration differs from training-start receipt")
    if exit_receipt.get("process_started_sha256") != sha(start_path):
        raise ValueError("process start receipt hash mismatch")
    for path, expected in reg["source_pins"].items():
        source = ROOT / path
        if not source.is_file() or sha(source) != expected:
            raise ValueError(f"registered source changed: {path}")
    pool_path = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
    pool_audit_path = ROOT / "results/dev_aux/task2627/rule15-successor-pool-audit.json"
    if sha(pool_path) != reg["root_pools_sha256"] or sha(pool_audit_path) != reg["root_pools_audit_sha256"]:
        raise ValueError("registered source-bound root pool or audit changed")

    seeds = plan["seeds"]
    rules = plan["domain"]["rules"]
    expected = {(rule, seed) for rule in rules for seed in seeds}
    queries_by_arm: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in read_jsonl(RUN / "queries.jsonl"):
        key = (row["rule"], row["seed"])
        if key not in expected:
            raise ValueError(f"unregistered arm in query stream: {key}")
        queries_by_arm[key].append(row)
    episodes_by_arm: dict[tuple[int, int], list[dict]] = defaultdict(list)
    episode_keys = set()
    for row in read_jsonl(RUN / "episodes.jsonl"):
        key = (row["rule"], row["seed"])
        if key not in expected:
            raise ValueError(f"unregistered arm in episode stream: {key}")
        episode_key = (*key, row["episode"])
        if episode_key in episode_keys:
            raise ValueError(f"duplicate episode closure: {episode_key}")
        episode_keys.add(episode_key)
        episodes_by_arm[key].append(row)
    if set(queries_by_arm) != expected or set(episodes_by_arm) != expected:
        raise ValueError("the one-shot run did not leave records for every registered arm")

    arms = []
    total_queries = total_episodes = total_nodes = total_actual = total_unknown = 0
    arm_receipts = {}
    node_cap = plan["training"]["nodes_per_arm_candidate_plus_foe"]
    for rule in rules:
        for seed in seeds:
            key = (rule, seed)
            query_rows = queries_by_arm[key]
            episode_rows = episodes_by_arm[key]
            counts = Counter()
            for query in query_rows:
                nodes = query.get("nodes")
                if type(nodes) is not int or nodes < 0 or nodes > query.get("requested_nodes", -1):
                    raise ValueError(f"invalid node receipt for arm {key}")
                counts["nodes"] += nodes
                counts["candidate_nodes" if query["learner_turn"] else "foe_nodes"] += nodes
                counts["queries"] += 1
                if not query["complete"]:
                    counts["incomplete_searches"] += 1
            for episode in episode_rows:
                counts["episodes"] += 1
                if episode["actual_outcome"] is None:
                    counts["UNKNOWN"] += 1
                else:
                    counts["actual_terminal"] += 1
                counts["nonzero_updates"] += bool(episode["stats"]["changed"])
                episode_queries = [q for q in query_rows if q["episode"] == episode["episode"]]
                if len(episode_queries) != episode["queries"]:
                    raise ValueError(f"query/episode receipt count differs for arm {key}")
                if sum(q["nodes"] for q in episode_queries) != episode["nodes"]:
                    raise ValueError(f"query/episode node count differs for arm {key}")
            if counts["nodes"] != node_cap:
                raise ValueError(f"arm {key} did not exactly reach its registered node cap")
            if counts["episodes"] != len(episode_rows):
                raise AssertionError("episode count reconstruction failed")
            initial = plan["initialization"]["weights_by_rule_seed"][f"{rule}:{seed}"]
            final = episode_rows[-1]["final_weights"]
            if episode_rows[-1]["seed"] != seed or episode_rows[-1]["rule"] != rule:
                raise ValueError(f"last episode does not match arm {key}")
            arm = {"rule": rule, "seed": seed, "initial_weights": initial,
                   "final_weights": final, "nodes": counts["nodes"],
                   "seconds": None, "counts": dict(counts), "status": "NODE_CAP"}
            arms.append(arm)
            arm_receipts[f"{rule}:{seed}"] = {
                "queries": len(query_rows), "episodes": len(episode_rows),
                "nodes": counts["nodes"], "actual_terminal": counts["actual_terminal"],
                "UNKNOWN": counts["UNKNOWN"], "nonzero_updates": counts["nonzero_updates"],
            }
            total_queries += counts["queries"]
            total_episodes += counts["episodes"]
            total_nodes += counts["nodes"]
            total_actual += counts["actual_terminal"]
            total_unknown += counts["UNKNOWN"]

    training_result = {
        "status": "COMPLETE", "expected_arms": len(expected), "arms": arms,
        "nodes": total_nodes, "episodes": total_episodes,
        "actual_terminal": total_actual, "UNKNOWN": total_unknown,
        "queries": total_queries, "seconds": exit_receipt["wall_seconds"],
        "plan_sha256": reg["plan_sha256"], "registration_sha256": sha(reg_path),
        "root_pools_sha256": reg["root_pools_sha256"],
        "scope": "Fixed-scale SAME TDLeaf training comparison on one feature-conditioned generated ruleset only.",
        "recovery": "Post-run summary reconstructed from the sole durable query/episode logs after the pinned trainer raised KeyError('rule_index') while checking the already-built arm keys. No search, sample, retry or top-up was performed. Per-arm seconds were not emitted and are null.",
    }
    report = {
        "status": "PASS_RECONSTRUCTED_ALL_REGISTERED_TRAINING_ARMS_FROM_DURABLE_LOGS",
        "original_launch_return_code": exit_receipt["return_code"],
        "failure": "KeyError('rule_index') at train.py:246 after all arm logs were closed; arm summaries use 'rule'.",
        "launch_exit_sha256": sha(exit_path), "launch_stderr_sha256": sha(stderr_path),
        "plan_sha256": sha(plan_path), "registration_sha256": sha(reg_path),
        "started_sha256": sha(start_path),
        "stdout_sha256": sha(stdout_path),
        "queries_sha256": sha(RUN / "queries.jsonl"),
        "episodes_sha256": sha(RUN / "episodes.jsonl"),
        "source_pin_count": len(reg["source_pins"]),
        "source_pins_match": True,
        "runner_wall_seconds": exit_receipt["wall_seconds"],
        "hard_seconds": plan["training"]["hard_seconds"],
        "nodes_per_arm_cap": node_cap,
        "arm_receipts": arm_receipts,
        "training_result_sha256": hashlib.sha256(
            (json.dumps(training_result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        ).hexdigest(),
        "policy": "Derived receipt only. Preserve the failed launcher receipt and require the independent full-history TD/outcome/cap audit before any evaluation binding.",
    }
    for path, value in ((OUT, training_result), (REPORT, report)):
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
