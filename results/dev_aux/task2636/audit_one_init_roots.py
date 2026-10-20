"""Independent replay, source, prefix-exposure and split audit for task2636."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
PLAN = TASK / "one-init-root-plan.json"
POOL = TASK / "one-init-root-pools.json"
PREFIXES = TASK / "exposed-prefix-inventory.json"
OUT = TASK / "one-init-root-audit.json"

sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv


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


def main() -> dict:
    if OUT.exists():
        raise FileExistsError(f"write-once root audit already exists: {OUT}")
    plan_raw = PLAN.read_bytes()
    plan = json.loads(plan_raw)
    pool_raw = POOL.read_bytes()
    pool = json.loads(pool_raw)
    prefix_raw = PREFIXES.read_bytes()
    prefix_doc = json.loads(prefix_raw)
    if pool.get("status") != "COMPLETE_PREFIX_DISJOINT_ROOT_POOLS_PREPARED_NOT_REGISTERED":
        raise ValueError("root pool is not a complete unregistered preparation")
    if pool.get("plan_sha256") != sha(plan_raw) or pool.get("prefix_inventory_sha256") != sha(prefix_raw):
        raise ValueError("pool source bindings do not match frozen plan/prefix inventory")
    if pool.get("runner_sha256") != plan.get("runner_sha256"):
        raise ValueError("root preparation runner binding mismatch")
    for rel, expected in plan["source_sha256"].items():
        if file_sha(ROOT / rel) != expected:
            raise ValueError(f"pinned source changed: {rel}")
    if file_sha(ROOT / plan["runner"]) != plan["runner_sha256"]:
        raise ValueError("root preparation runner changed")

    index_path = ROOT / plan["candidate_index"]
    index_raw = index_path.read_bytes()
    if sha(index_raw) != plan["candidate_index_sha256"]:
        raise ValueError("candidate-index hash mismatch")
    index = json.loads(index_raw)
    if len(index.get("rows", [])) != 16 or pool.get("candidate_count") != 16:
        raise ValueError("candidate count mismatch")

    candidates = []
    for i, row in enumerate(index["rows"]):
        expected_rule_hash = plan["candidate_rule_sha256"].get(row["source_file"])
        raw_rule = (ROOT / row["source_file"]).read_bytes()
        if expected_rule_hash != row["ruleset_sha256"] or sha(raw_rule) != expected_rule_hash:
            raise ValueError(f"candidate rule pin mismatch: {row['source_file']}")
        compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)))
        fp = GameSession(compiled).to_record().ruleset_fingerprint
        candidates.append({"index": i, "seed": row["seed"], "rule_path": row["source_file"],
                           "rule_sha256": expected_rule_hash, "fingerprint": fp, "compiled": compiled})
    if len({c["fingerprint"] for c in candidates}) != 16:
        raise ValueError("candidate ruleset fingerprints are not unique")

    prior_prefixes: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for c in prefix_doc["candidates"]:
        for p in c["observed_prefixes"]:
            prior_prefixes[c["ruleset_fingerprint"]][p["length"]].add(p["sha256"])
    if prefix_doc.get("status") != "COMPLETE_REPLAYED_EXACT_PREFIX_INVENTORY_ONLY_NO_ROOTS_SELECTED":
        raise ValueError("prior prefix inventory is incomplete")

    counts = {"training": Counter(), "evaluation": Counter()}
    keys = {"training": defaultdict(set), "evaluation": defaultdict(set)}
    hashes = {"training": defaultdict(set), "evaluation": defaultdict(set)}
    replay_count = 0
    prefix_checks = 0
    active_feature_roots = 0
    for split, roots, family_range, expected_per_rule in (
        ("training", pool["training_roots"], plan["training_family_range"], plan["training_roots_per_candidate"]),
        ("evaluation", pool["evaluation_roots"], plan["evaluation_family_range"], plan["evaluation_roots_per_candidate"]),
    ):
        for row in roots:
            idx = row["candidate_index"]
            if not isinstance(idx, int) or idx < 0 or idx >= len(candidates):
                raise ValueError(f"bad candidate index in {split}")
            c = candidates[idx]
            fp = c["fingerprint"]
            record = row["record"]
            key = canonical(record)
            record_hash = sha(key)
            if (row["candidate_seed"] != c["seed"] or row["rule_path"] != c["rule_path"] or
                    row["rule_sha256"] != c["rule_sha256"] or row["ruleset_fingerprint"] != fp):
                raise ValueError(f"root/candidate binding mismatch in {split}")
            if record.get("ruleset_fingerprint") != fp or row["record_sha256"] != record_hash:
                raise ValueError(f"root fingerprint/hash mismatch in {split}")
            if not family_range[0] <= row["family"] < family_range[1]:
                raise ValueError(f"root family outside frozen range in {split}")
            actions = record.get("actions")
            if not isinstance(actions, list) or len(actions) != plan["prefix_plies"]:
                raise ValueError(f"root has wrong history length in {split}")
            for length in range(1, plan["prefix_plies"] + 1):
                prefix_hash = sha(canonical({"ruleset_fingerprint": fp, "actions": actions[:length]}))
                prefix_checks += 1
                if prefix_hash in prior_prefixes[fp].get(length, set()):
                    raise ValueError(f"root overlaps exposed task2635 prefix in {split} candidate {idx}")
            if key in keys[split][fp]:
                raise ValueError(f"duplicate root in {split} candidate {idx}")
            keys[split][fp].add(key)
            hashes[split][fp].add(record_hash)

            typed = deserialize_game_record(key.decode("utf-8"))
            replayed = GameSession.replay(c["compiled"], typed)
            env = FixedScaleSessionEnv(replayed, unit_type=plan["unit_type"])
            if replayed.to_record() != typed or env.terminal() is not None:
                raise ValueError(f"root replay/terminal mismatch in {split} candidate {idx}")
            features = list(env.features())
            channels = [list(name) for name in env.names]
            if features != row["features"] or channels != row["channels"]:
                raise ValueError(f"root feature/channel mismatch in {split} candidate {idx}")
            if not any(features[1:]):
                raise ValueError(f"root lacks active non-unit feature in {split} candidate {idx}")
            active_feature_roots += 1
            counts[split][idx] += 1
            replay_count += 1
        if dict(counts[split]) != {i: expected_per_rule for i in range(16)}:
            raise ValueError(f"wrong {split} per-candidate counts: {dict(counts[split])}")

    train_eval_overlap = {}
    for c in candidates:
        fp = c["fingerprint"]
        overlap = len(keys["training"][fp] & keys["evaluation"][fp])
        train_eval_overlap[str(c["index"])] = overlap
        if overlap:
            raise ValueError(f"training/evaluation exact record overlap for candidate {c['index']}")

    result = {
        "status": "PASS_SOURCE_PREFIX_HISTORY_FEATURE_REPLAY_AND_SPLIT_AUDIT",
        "root_plan_sha256": sha(plan_raw), "root_pool_sha256": sha(pool_raw),
        "prefix_inventory_sha256": sha(prefix_raw),
        "candidate_index_sha256": sha(index_raw),
        "candidate_count": len(candidates), "training_roots": sum(counts["training"].values()),
        "evaluation_roots": sum(counts["evaluation"].values()),
        "replayed_roots": replay_count, "active_feature_roots": active_feature_roots,
        "prior_prefix_checks": prefix_checks,
        "train_eval_exact_overlap_by_candidate": train_eval_overlap,
        "training_counts_by_candidate": {str(k): counts["training"][k] for k in sorted(counts["training"])},
        "evaluation_counts_by_candidate": {str(k): counts["evaluation"][k] for k in sorted(counts["evaluation"])},
        "training_or_evaluation_started": False, "outcome_or_search_fields_used": False,
        "scope": "Exact prior action-prefix exclusion and exact training/evaluation start-record disjointness; no transposition or distributional independence claim.",
    }
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n").encode("utf-8")
    OUT.write_bytes(raw)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
