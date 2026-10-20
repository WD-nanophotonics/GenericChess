"""Independent exact-history and replay audit for the prepared task2624 pools."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

POOL_PATH = ROOT / "results/dev_aux/task2624/root-pools-v2.json"
OUT = ROOT / "results/dev_aux/task2624/root-pools-audit.json"
RULES = (271001, 271002, 271003, 271004)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def walk_records(value):
    if isinstance(value, dict):
        if isinstance(value.get("ruleset_fingerprint"), str) and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child)


def row_records(row: dict):
    for key in ("record_before", "record_after", "initial_record", "final_record", "record"):
        value = row.get(key)
        if isinstance(value, dict):
            yield value


def main() -> None:
    doc = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    if doc.get("status") != "OUTCOME_BLIND_EXACT_HISTORY_ROOT_POOLS_PREPARED_NOT_REGISTERED":
        raise ValueError("unexpected root-pool state")
    compiled = {}
    fingerprints = {}
    for rule in RULES:
        path = ROOT / f"results/dev_aux/task2525/rules-{rule}.json"
        raw = path.read_bytes()
        if doc["selection_inputs"]["rule_sha256"].get(path.relative_to(ROOT).as_posix()) != digest(raw):
            raise ValueError(f"rule source changed: {rule}")
        compiled[rule] = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
        fingerprint = GameSession(compiled[rule]).to_record().ruleset_fingerprint
        fingerprints[fingerprint] = rule

    prior = {rule: set() for rule in RULES}
    source_audit = []
    for receipt in doc["selection_inputs"]["history_files"]:
        path = ROOT / receipt["path"]
        if receipt["status"] == "MISSING":
            if path.exists():
                raise ValueError(f"source appeared after prep; reprepare required: {receipt['path']}")
            continue
        seen = 0
        if receipt["status"] == "READ":
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for line in stream:
                    hasher.update(line)
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    for record in row_records(row):
                        rule = fingerprints.get(record.get("ruleset_fingerprint"))
                        if rule is not None:
                            prior[rule].add(canon(record)); seen += 1
            source_hash = hasher.hexdigest()
        elif receipt["status"] == "READ_JSON_RECORDS_ONLY":
            raw = path.read_bytes()
            source_hash = digest(raw)
            for record in walk_records(json.loads(raw)):
                rule = fingerprints.get(record.get("ruleset_fingerprint"))
                if rule is not None:
                    prior[rule].add(canon(record)); seen += 1
        else:
            raise ValueError(f"unknown source receipt state: {receipt['status']}")
        if source_hash != receipt["sha256"]:
            raise ValueError(f"history source changed after preparation: {receipt['path']}")
        if seen != receipt["target_record_occurrences"]:
            raise ValueError(f"record count differs for {receipt['path']}: {seen}")
        source_audit.append({"path": receipt["path"], "status": receipt["status"],
                             "target_record_occurrences": seen, "sha256": source_hash})

    seen_train, seen_eval = set(), set()
    group_counts = {"training": Counter(), "evaluation": Counter()}
    replay_count = 0
    pairwise_overlap = Counter()
    for label, rows in (("training", doc["training_roots"]), ("evaluation", doc["evaluation_roots"])):
        local = set()
        for row in rows:
            rule = row["rule"]
            record = row["record"]
            key = canon(record)
            if rule not in RULES:
                raise ValueError(f"unknown rule in {label} roots: {rule}")
            expected_fingerprint = GameSession(compiled[rule]).to_record().ruleset_fingerprint
            if record.get("ruleset_fingerprint") != expected_fingerprint:
                raise ValueError(f"rule/fingerprint mismatch: {label} {rule}")
            if digest(key) != row["record_sha256"] or key in local:
                raise ValueError(f"bad hash or duplicate in {label} roots")
            if key in prior[rule]:
                raise ValueError(f"root overlaps an enumerated prior full history: {label} {rule}")
            if len(record.get("actions", [])) != 8:
                raise ValueError(f"not an 8-action full history: {label} {rule}")
            typed_record = deserialize_game_record(json.dumps(record))
            replayed = GameSession.replay(compiled[rule], typed_record)
            env = FixedScaleSessionEnv(replayed)
            if replayed.to_record() != typed_record or env.terminal() is not None:
                raise ValueError(f"full-history replay or terminal check failed: {label} {rule}")
            if list(env.features()) != row["features"] or [list(x) for x in env.names] != row["channels"]:
                raise ValueError(f"feature/channel receipt mismatch: {label} {rule}")
            if not any(row["features"][1:]):
                raise ValueError(f"root lacks predeclared active feature: {label} {rule}")
            local.add(key)
            group_counts[label][rule] += 1
            replay_count += 1
            (seen_train if label == "training" else seen_eval).add((rule, key))

    for rule in RULES:
        if group_counts["training"][rule] != 120 or group_counts["evaluation"][rule] != 16:
            raise ValueError(f"wrong frozen root count: {rule}")
        pairwise_overlap[rule] = len({key for r, key in seen_train if r == rule}
                                     & {key for r, key in seen_eval if r == rule})
        if pairwise_overlap[rule]:
            raise ValueError(f"train/evaluation overlap: {rule}")

    result = {
        "status": "PASS_EXACT_HISTORY_SOURCE_HASH_REPLAY_FEATURE_AND_DISJOINTNESS_AUDIT",
        "root_pools_sha256": digest(POOL_PATH.read_bytes()),
        "prior_sources_verified": len(source_audit),
        "prior_unique_full_histories_by_rule": {rule: len(prior[rule]) for rule in RULES},
        "training_roots_by_rule": dict(group_counts["training"]),
        "evaluation_roots_by_rule": dict(group_counts["evaluation"]),
        "exact_train_eval_overlap_by_rule": dict(pairwise_overlap),
        "replayed_roots": replay_count,
        "source_audit": source_audit,
        "scope": "Exact records in enumerated prior evidence only; no descendant, semantic/transposition, or distributional independence claim.",
    }
    raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    OUT.write_bytes(raw)
    print(json.dumps({k: v for k, v in result.items() if k != "source_audit"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
