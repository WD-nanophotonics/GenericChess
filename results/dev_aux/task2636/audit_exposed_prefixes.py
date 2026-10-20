"""Replay and inventory exact action prefixes exposed by task2635 histories."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / "results/dev_aux/task2636"
PLAN = TASK / "prefix-audit-plan.json"
OUT = TASK / "exposed-prefix-inventory.json"
STATUS = TASK / "prefix-audit-status.json"
HARD_SECONDS = 120.0

sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession


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


def save_status(payload: dict) -> None:
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")


def main() -> dict:
    if OUT.exists():
        raise FileExistsError(f"write-once prefix inventory already exists: {OUT}")
    plan_raw = PLAN.read_bytes()
    plan = json.loads(plan_raw)
    inputs = plan["inputs"]
    for rel, expected in (
        (inputs["original_inventory_plan"], inputs["original_inventory_plan_sha256"]),
        (inputs["candidate_index"], inputs["candidate_index_sha256"]),
        (inputs["episode_source"], inputs["episode_source_sha256"]),
        (inputs["trajectory_plan"], inputs["trajectory_plan_sha256"]),
        (inputs["inventory"], inputs["inventory_sha256"]),
    ):
        actual = file_sha(ROOT / rel)
        if actual != expected:
            raise ValueError(f"pinned source changed: {rel}")

    inventory = json.loads((ROOT / inputs["inventory"]).read_text(encoding="utf-8"))
    if inventory.get("status") != "COMPLETE_DYNAMIC_EXACT_HISTORY_INVENTORY_ONLY_NO_ROOTS_WRITTEN":
        raise ValueError("the dynamic inventory is not complete")
    if inventory.get("candidate_count") != 16 or inventory.get("total_exact_record_occurrences") != 64:
        raise ValueError("unexpected candidate/history inventory cardinality")
    expected_source = inputs["episode_source"]
    observed_sources = {
        source["path"]: source["sha256"]
        for candidate in inventory["candidate_histories"]
        for source in candidate["matched_sources"]
    }
    if observed_sources != {expected_source: inputs["episode_source_sha256"]}:
        raise ValueError(f"inventory matched source set differs: {observed_sources}")

    index_path = ROOT / inputs["candidate_index"]
    index_raw = index_path.read_bytes()
    if sha(index_raw) != inputs["candidate_index_sha256"]:
        raise ValueError("candidate index pin mismatch")
    index = json.loads(index_raw)
    if index.get("candidate_count") != 16 or len(index.get("rows", [])) != 16:
        raise ValueError("candidate index is not the frozen 16-rule set")
    trajectory_plan = json.loads((ROOT / inputs["trajectory_plan"]).read_text(encoding="utf-8"))
    if (trajectory_plan.get("candidate_index_sha256") != inputs["candidate_index_sha256"] or
            trajectory_plan.get("candidate_count") != 16 or
            trajectory_plan.get("trajectories_per_candidate") != 4):
        raise ValueError("unexpected pinned trajectory plan")

    candidates = {}
    for candidate_index, row in enumerate(index["rows"]):
        rule_path = ROOT / row["source_file"]
        raw_rule = rule_path.read_bytes()
        if sha(raw_rule) != row["ruleset_sha256"]:
            raise ValueError(f"candidate rule source changed: {row['source_file']}")
        compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)))
        fp = GameSession(compiled).to_record().ruleset_fingerprint
        if fp != inventory["candidate_histories"][candidate_index]["ruleset_fingerprint"]:
            raise ValueError(f"candidate fingerprint mismatch at index {candidate_index}")
        candidates[fp] = {
            "candidate_index": candidate_index,
            "seed": row["seed"],
            "rule_path": row["source_file"],
            "rule_sha256": row["ruleset_sha256"],
            "compiled": compiled,
            "expected_records": set(inventory["candidate_histories"][candidate_index]["exact_record_sha256"]),
            "seen_records": set(),
            "prefixes": defaultdict(dict),
            "prefix_counts": Counter(),
        }
    if len(candidates) != 16:
        raise ValueError("compiled candidate fingerprints are not unique")

    started = time.perf_counter()
    source = ROOT / expected_source
    source_hash = hashlib.sha256()
    rows_seen = 0
    replicates = set()
    for line_no, raw_line in enumerate(source.open("rb"), 1):
        if time.perf_counter() - started >= HARD_SECONDS:
            save_status({"status": "HARD_CAP_NO_COMPLETE_PREFIX_INVENTORY",
                         "rows_seen": rows_seen, "outputs_written": False,
                         "elapsed_seconds": time.perf_counter() - started})
            raise TimeoutError("120-second prefix audit cap reached")
        source_hash.update(raw_line)
        if not raw_line.strip():
            continue
        episode = json.loads(raw_line)
        record = episode.get("full_history_record")
        if not isinstance(record, dict) or not isinstance(record.get("actions"), list):
            raise ValueError(f"missing complete history at line {line_no}")
        fp = record.get("ruleset_fingerprint")
        candidate = candidates.get(fp)
        if candidate is None:
            raise ValueError(f"unknown candidate fingerprint at line {line_no}")
        replicate_index = episode.get("replicate")
        expected_trajectory_seed = (trajectory_plan["trajectory_seed_start"] +
                                    candidate["candidate_index"] * trajectory_plan["trajectories_per_candidate"] +
                                    replicate_index if isinstance(replicate_index, int) else -1)
        if (episode.get("candidate_index") != candidate["candidate_index"] or
                episode.get("seed") != expected_trajectory_seed or
                episode.get("ruleset_sha256") != candidate["rule_sha256"]):
            raise ValueError(f"episode/candidate binding mismatch at line {line_no}")
        replicate = (episode["candidate_index"], episode["seed"], episode.get("replicate"))
        if replicate in replicates:
            raise ValueError(f"duplicate candidate replicate at line {line_no}")
        replicates.add(replicate)

        encoded_record = canonical(record)
        record_hash = sha(encoded_record)
        candidate["seen_records"].add(record_hash)
        typed_record = deserialize_game_record(encoded_record.decode("utf-8"))
        replayed = GameSession.replay(candidate["compiled"], typed_record)
        if replayed.to_record() != typed_record:
            raise ValueError(f"complete history replay mismatch at line {line_no}")

        actions = record["actions"]
        if not actions:
            raise ValueError(f"empty exposed history at line {line_no}")
        for length in range(1, min(8, len(actions)) + 1):
            prefix = actions[:length]
            prefix_hash = sha(canonical({"ruleset_fingerprint": fp, "actions": prefix}))
            candidate["prefixes"][length][prefix_hash] = prefix
            candidate["prefix_counts"][length] += 1
        rows_seen += 1

    if source_hash.hexdigest() != inputs["episode_source_sha256"]:
        raise ValueError("episode source changed during audit")
    if rows_seen != 64 or len(replicates) != 64:
        raise ValueError(f"expected64 histories/replicates, saw {rows_seen}/{len(replicates)}")
    for candidate in candidates.values():
        if candidate["seen_records"] != candidate["expected_records"]:
            raise ValueError(f"exact-record hashes differ for candidate {candidate['candidate_index']}")

    candidate_rows = []
    total_prefix_records = total_unique_prefixes = 0
    for fp, candidate in sorted(candidates.items(), key=lambda item: item[1]["candidate_index"]):
        prefix_rows = []
        for length in sorted(candidate["prefixes"]):
            prefixes = candidate["prefixes"][length]
            prefix_rows.extend({"length": length, "sha256": key, "actions": actions}
                               for key, actions in sorted(prefixes.items()))
            total_unique_prefixes += len(prefixes)
            total_prefix_records += candidate["prefix_counts"][length]
        candidate_rows.append({
            "candidate_index": candidate["candidate_index"], "seed": candidate["seed"],
            "rule_path": candidate["rule_path"], "rule_sha256": candidate["rule_sha256"],
            "ruleset_fingerprint": fp, "complete_histories_replayed": len(candidate["seen_records"]),
            "unique_prefixes_by_length": {str(length): len(rows)
                                           for length, rows in sorted(candidate["prefixes"].items())},
            "observed_prefixes": prefix_rows,
        })

    result = {
        "status": "COMPLETE_REPLAYED_EXACT_PREFIX_INVENTORY_ONLY_NO_ROOTS_SELECTED",
        "task": plan["task"], "plan_sha256": sha(plan_raw),
        "inventory_sha256": inputs["inventory_sha256"],
        "candidate_index_sha256": inputs["candidate_index_sha256"],
        "episode_source": expected_source, "episode_source_sha256": source_hash.hexdigest(),
        "candidate_count": len(candidate_rows), "complete_histories_replayed": rows_seen,
        "unique_replicate_keys": len(replicates), "prefix_lengths": [1, 2, 3, 4, 5, 6, 7, 8],
        "prefix_record_occurrences": total_prefix_records,
        "unique_rule_bound_prefixes": total_unique_prefixes,
        "candidates": candidate_rows,
        "root_pool_created": False, "training_or_evaluation_started": False,
        "outcome_or_ending_fields_read": False, "search_queries": 0,
        "elapsed_seconds": time.perf_counter() - started,
        "limits": plan["limits"],
    }
    raw = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False,
                      allow_nan=False) + "\n").encode("utf-8")
    with OUT.open("xb") as stream:
        stream.write(raw)
    receipt = {"status": result["status"], "inventory_sha256": sha(raw),
               "candidate_count": len(candidate_rows), "complete_histories_replayed": rows_seen,
               "prefix_record_occurrences": total_prefix_records,
               "unique_rule_bound_prefixes": total_unique_prefixes,
               "elapsed_seconds": result["elapsed_seconds"], "outputs_written": True}
    save_status(receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
