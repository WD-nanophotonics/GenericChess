"""Prepare a prefix-disjoint 16-rule root pool; no learner/search execution."""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
PLAN = TASK / "one-init-root-plan.json"
OUT = TASK / "one-init-root-pools.json"
STATUS = TASK / "one-init-root-preparation-status.json"

sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from tools.local_agent.environment import require_identity


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def record_key(record: dict) -> bytes:
    return canonical(record)


def read_stop() -> bool:
    rollout = json.loads((ROOT / ".local_agent/rollout.json").read_text(encoding="utf-8"))
    slack = json.loads((ROOT / ".local_agent/slack.json").read_text(encoding="utf-8"))
    return bool(rollout.get("user_paused") or slack.get("stopped"))


def save_status(payload: dict) -> None:
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def verify_plan(plan: dict, plan_raw: bytes) -> tuple[dict, dict[str, dict]]:
    if file_sha(Path(__file__)) != plan.get("runner_sha256"):
        raise ValueError("root preparation runner changed after plan freeze")
    for rel, expected in plan["source_sha256"].items():
        if file_sha(ROOT / rel) != expected:
            raise ValueError(f"pinned source changed: {rel}")
    prefix_doc = json.loads((ROOT / plan["prefix_inventory"]).read_text(encoding="utf-8"))
    if prefix_doc.get("status") != "COMPLETE_REPLAYED_EXACT_PREFIX_INVENTORY_ONLY_NO_ROOTS_SELECTED":
        raise ValueError("prefix inventory is incomplete")
    prefixes: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for candidate in prefix_doc["candidates"]:
        for prefix in candidate["observed_prefixes"]:
            prefixes[candidate["ruleset_fingerprint"]][prefix["length"]].add(prefix["sha256"])
    return prefix_doc, prefixes


def main() -> dict:
    require_identity()
    if OUT.exists() or STATUS.exists():
        raise FileExistsError("task2636 root preparation is write-once; preserve existing outputs")
    if read_stop():
        raise RuntimeError("active DEV_AUX stop flag; root preparation refused")
    plan_raw = PLAN.read_bytes()
    plan = json.loads(plan_raw)
    prefix_doc, prefix_hashes = verify_plan(plan, plan_raw)
    index_raw = (ROOT / plan["candidate_index"]).read_bytes()
    index = json.loads(index_raw)
    if sha(index_raw) != plan["candidate_index_sha256"] or len(index.get("rows", [])) != 16:
        raise ValueError("candidate index changed or is not the frozen 16-rule set")

    candidates = []
    for index_no, row in enumerate(index["rows"]):
        rule_path = ROOT / row["source_file"]
        rule_raw = rule_path.read_bytes()
        if sha(rule_raw) != row["ruleset_sha256"]:
            raise ValueError(f"candidate rule source changed: {row['source_file']}")
        compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))
        fingerprint = GameSession(compiled).to_record().ruleset_fingerprint
        if fingerprint not in prefix_hashes:
            raise ValueError(f"candidate {index_no} has no bound prior-prefix set")
        candidates.append({"index": index_no, "seed": row["seed"],
                           "rule_path": row["source_file"], "rule_sha256": row["ruleset_sha256"],
                           "fingerprint": fingerprint, "compiled": compiled})
    if len({row["fingerprint"] for row in candidates}) != 16:
        raise ValueError("candidate ruleset fingerprints are not unique")

    started = time.perf_counter()
    hard_seconds = plan["preparation_hard_cap_seconds"]
    total_examined = 0
    all_roots: dict[str, list[dict]] = {"training": [], "evaluation": []}
    stats: dict[str, dict] = {}
    train_keys: dict[str, set[bytes]] = defaultdict(set)

    def candidate_root(candidate: dict, family: int):
        env = FixedScaleSessionEnv(GameSession(candidate["compiled"]), unit_type="P")
        rng = random.Random(candidate["seed"] * 1_000_000 + family)
        for _ in range(plan["prefix_plies"]):
            if env.terminal() is not None:
                break
            legal = sorted((action for action in env.actions() if action.kind == "ACTION"), key=repr)
            if not legal:
                break
            env.push(rng.choice(legal))
        record = env.record()
        if len(record.get("actions", ())) != plan["prefix_plies"] or env.terminal() is not None:
            return None, "invalid_or_terminal"
        features = list(env.features())
        if not any(features[1:]):
            return None, "inactive_feature"
        key = record_key(record)
        return {"record": record, "record_sha256": sha(key), "features": features,
                "channels": [list(item) for item in env.names], "key": key}, None

    def overlaps_exposed(candidate: dict, actions: list[dict]) -> bool:
        fp = candidate["fingerprint"]
        for length in range(1, plan["prefix_plies"] + 1):
            prefix_hash = sha(canonical({"ruleset_fingerprint": fp, "actions": actions[:length]}))
            if prefix_hash in prefix_hashes[fp].get(length, set()):
                return True
        return False

    def select(label: str, scan_range: list[int], amount: int) -> None:
        nonlocal total_examined
        selected_by_candidate = {candidate["fingerprint"]: 0 for candidate in candidates}
        counts = Counter()
        local_keys: dict[str, set[bytes]] = defaultdict(set)
        for family in range(scan_range[0], scan_range[1]):
            if time.perf_counter() - started >= hard_seconds:
                raise TimeoutError(f"fixed {label} family range exceeded {hard_seconds}s preparation cap")
            if family % 100 == 0:
                if read_stop():
                    raise RuntimeError("DEV_AUX stop observed during root preparation")
                save_status({"status": "PREPARING", "stage": label, "family": family,
                             "total_examined": total_examined,
                             "elapsed_seconds": time.perf_counter() - started,
                             "outputs_written": False})
            for candidate in candidates:
                fp = candidate["fingerprint"]
                if selected_by_candidate[fp] >= amount:
                    continue
                generated, reason = candidate_root(candidate, family)
                total_examined += 1
                counts["examined_rule_family_pairs"] += 1
                if reason:
                    counts[reason] += 1
                    continue
                actions = generated["record"]["actions"]
                if overlaps_exposed(candidate, actions):
                    counts["exposed_prefix_rejections"] += 1
                    continue
                key = generated["key"]
                if key in local_keys[fp]:
                    counts["within_pool_exact_duplicate_rejections"] += 1
                    continue
                if label == "evaluation" and key in train_keys[fp]:
                    counts["train_evaluation_exact_overlap_rejections"] += 1
                    continue
                local_keys[fp].add(key)
                if label == "training":
                    train_keys[fp].add(key)
                all_roots[label].append({
                    "candidate_index": candidate["index"], "candidate_seed": candidate["seed"],
                    "rule_path": candidate["rule_path"], "rule_sha256": candidate["rule_sha256"],
                    "ruleset_fingerprint": fp, "family": family,
                    "record": generated["record"], "record_sha256": generated["record_sha256"],
                    "features": generated["features"], "channels": generated["channels"],
                })
                selected_by_candidate[fp] += 1
            if all(value == amount for value in selected_by_candidate.values()):
                break
        if any(value != amount for value in selected_by_candidate.values()):
            raise RuntimeError(f"fixed {label} family range short: selected={selected_by_candidate}")
        stats[label] = {"family_range": scan_range, "selected_per_candidate": amount,
                        "selected_total": sum(selected_by_candidate.values()),
                        "selected_by_candidate_index": {str(c["index"]): selected_by_candidate[c["fingerprint"]]
                                                        for c in candidates},
                        **dict(counts)}

    try:
        select("training", plan["training_family_range"], plan["training_roots_per_candidate"])
        select("evaluation", plan["evaluation_family_range"], plan["evaluation_roots_per_candidate"])
    except Exception as exc:
        save_status({"status": "PREPARATION_FAILED_NO_POOL_WRITTEN", "error_type": type(exc).__name__,
                     "error": str(exc), "total_examined": total_examined,
                     "elapsed_seconds": time.perf_counter() - started, "outputs_written": False})
        raise

    result = {
        "status": "COMPLETE_PREFIX_DISJOINT_ROOT_POOLS_PREPARED_NOT_REGISTERED",
        "plan_sha256": sha(plan_raw), "runner_sha256": file_sha(Path(__file__)),
        "candidate_index_sha256": plan["candidate_index_sha256"],
        "prefix_inventory_sha256": plan["prefix_inventory_sha256"],
        "candidate_count": len(candidates), "prefix_plies": plan["prefix_plies"],
        "prefix_exclusions_checked": True,
        "exposed_prefixes_per_candidate": {
            str(row["candidate_index"]): row["unique_prefixes_by_length"]
            for row in prefix_doc["candidates"]},
        "source_sha256": plan["source_sha256"], "cost_estimate": plan["cost_estimate"],
        "preparation_elapsed_seconds": time.perf_counter() - started,
        "total_examined_rule_family_pairs": total_examined,
        "training": stats["training"], "evaluation": stats["evaluation"],
        "training_roots": all_roots["training"], "evaluation_roots": all_roots["evaluation"],
        "root_pool_registered": False, "learner_or_search_started": False,
        "outcomes_or_search_values_used": False,
        "limits": plan["limits"],
    }
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n").encode("utf-8")
    with OUT.open("xb") as stream:
        stream.write(raw)
    receipt = {"status": result["status"], "root_pool_sha256": sha(raw),
               "preparation_elapsed_seconds": result["preparation_elapsed_seconds"],
               "total_examined_rule_family_pairs": total_examined,
               "training_roots": stats["training"]["selected_total"],
               "evaluation_roots": stats["evaluation"]["selected_total"],
               "outputs_written": True}
    save_status(receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
