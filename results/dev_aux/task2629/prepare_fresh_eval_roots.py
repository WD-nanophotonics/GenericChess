"""Select a new outcome-blind rules15 evaluation-only root panel."""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".local_agent/devaux_pydeps"))
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity

OUT = ROOT / "results/dev_aux/task2629"
POOL = OUT / "fresh-evaluation-roots.json"
STATUS = OUT / "root-preparation-status.json"
INVENTORY = ROOT / "results/dev_aux/task2627/source-inventory-v2.json"
OLD_POOL = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
TASK2628_RUN = ROOT / "results/dev_aux/task2628/run"
RULE = ROOT / "results/dev_aux/task2433/rules-15.json"
RULE_REL = RULE.relative_to(ROOT).as_posix()
FAMILY_RANGE = range(300_000, 350_000)
GENERATOR_SEED = 2_433_017
PREFIX_PLIES = 8
ROOTS_REQUIRED = 16
HARD_SECONDS = 180.0


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def walk_records(value: object):
    if isinstance(value, dict):
        if isinstance(value.get("ruleset_fingerprint"), str) and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child)


def load_records(path: Path, fingerprint: str):
    if path.suffix.lower() == ".jsonl":
        with path.open("rb") as stream:
            needle = fingerprint.encode("ascii")
            for line in stream:
                if needle not in line:
                    continue
                yield from (row for row in walk_records(json.loads(line))
                            if row.get("ruleset_fingerprint") == fingerprint)
    else:
        raw = path.read_bytes()
        if fingerprint.encode("ascii") in raw:
            yield from (row for row in walk_records(json.loads(raw))
                        if row.get("ruleset_fingerprint") == fingerprint)


def main() -> None:
    require_identity()
    OUT.mkdir(parents=True, exist_ok=True)
    if POOL.exists() or STATUS.exists():
        raise FileExistsError("task2629 root preparation is write-once")
    began = time.perf_counter()
    rule_raw = RULE.read_bytes()
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))
    fingerprint = GameSession(compiled).to_record().ruleset_fingerprint
    inventory_raw = INVENTORY.read_bytes()
    inventory = json.loads(inventory_raw)
    if inventory["candidate"]["ruleset_fingerprint"] != fingerprint:
        raise ValueError("prior exact-history inventory is for another ruleset")

    excluded: set[bytes] = set()
    source_receipts = []
    for source in inventory["matched_sources"]:
        path = ROOT / source["path"]
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != source["sha256"]:
            raise ValueError(f"pinned history source changed: {source['path']}")
        found = list(load_records(path, fingerprint))
        unique = {canon(row) for row in found}
        if (len(found) != source["record_occurrences"]
                or len(unique) != source["unique_records_in_file"]):
            raise ValueError(f"exact-history inventory mismatch: {source['path']}")
        excluded.update(unique)
        source_receipts.append({"path": source["path"], "sha256": h.hexdigest(),
                                "occurrences": len(found), "unique": len(unique)})
    if sorted(sha(key) for key in excluded) != inventory["unique_record_sha256"]:
        raise ValueError("reconstructed exact-history set differs from source inventory")
    if inventory.get("matched_compressed_sources"):
        raise ValueError("compressed historical sources need explicit parsing support")

    old_pool_raw = OLD_POOL.read_bytes()
    old_pool = json.loads(old_pool_raw)
    old_pool_records = list(walk_records(old_pool))
    old_pool_keys = {canon(row) for row in old_pool_records
                     if row.get("ruleset_fingerprint") == fingerprint}
    excluded.update(old_pool_keys)
    source_receipts.append({"path": OLD_POOL.relative_to(ROOT).as_posix(),
                            "sha256": sha(old_pool_raw), "unique": len(old_pool_keys),
                            "mode": "ALL_OLD_TRAIN_AND_EVALUATION_ROOTS"})

    # The task2628 registered learner/evaluator generated additional histories
    # after the older inventory. Include every complete or partial query/game
    # record without reading W/L/D fields for root selection.
    new_paths = [TASK2628_RUN / name for name in
                 ("queries.jsonl", "episodes.jsonl", "eval-queries.jsonl", "eval-games.jsonl")]
    for path in new_paths:
        h = hashlib.sha256()
        found_keys: set[bytes] = set()
        with path.open("rb") as stream:
            for line in stream:
                h.update(line)
                if fingerprint.encode("ascii") not in line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    raise ValueError(f"malformed durable task2628 history row: {path.name}")
                found_keys.update(canon(record) for record in walk_records(row)
                                  if record.get("ruleset_fingerprint") == fingerprint)
        excluded.update(found_keys)
        source_receipts.append({"path": path.relative_to(ROOT).as_posix(),
                                "sha256": h.hexdigest(), "unique": len(found_keys),
                                "mode": "ALL_TASK2628_QUERY_EPISODE_AND_EVALUATION_HISTORIES"})

    records = []
    seen: set[bytes] = set()
    tested = invalid = overlap = duplicate = 0
    status = {"status": "PREPARING_OUTCOME_BLIND_EVALUATION_ROOTS",
              "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "rule_sha256": sha(rule_raw), "prior_inventory_sha256": sha(inventory_raw),
              "old_pool_sha256": sha(old_pool_raw), "generator_seed": GENERATOR_SEED,
              "family_range": [FAMILY_RANGE.start, FAMILY_RANGE.stop],
              "required_roots": ROOTS_REQUIRED, "prefix_plies": PREFIX_PLIES,
              "hard_cap_seconds": HARD_SECONDS, "outputs_written": False}
    STATUS.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for family in FAMILY_RANGE:
        if time.perf_counter() - began >= HARD_SECONDS:
            status.update(status="HARD_CAP_REACHED_NO_POOL", tested_families=tested,
                          selected=len(records), elapsed_seconds=time.perf_counter() - began)
            STATUS.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise TimeoutError("root-preparation hard cap reached; no evaluation pool written")
        tested += 1
        env = FixedScaleSessionEnv(GameSession(compiled))
        prefix(env, GENERATOR_SEED, family, PREFIX_PLIES)
        record = env.record()
        if len(record.get("actions", [])) != PREFIX_PLIES or env.terminal() is not None:
            invalid += 1
            continue
        env.replay()
        position = env.session.state.position
        eligible = []
        for owner in (0, 1):
            hand_r = sum(n for base, n in position.hands[owner].counts if base == "R")
            board_r = sum(1 for piece in position.board if piece is not None and piece.owner == owner
                          and piece.current_type_id == "R")
            promoted_p = sum(1 for piece in position.board if piece is not None and piece.owner == owner
                             and piece.base_type_id == "P" and piece.current_type_id == "R")
            if hand_r and board_r and promoted_p:
                eligible.append((owner, hand_r, board_r, promoted_p))
        if not eligible:
            invalid += 1
            continue
        owner, hand_r, board_r, promoted_p = eligible[0]
        key = canon(record)
        if key in excluded:
            overlap += 1
            continue
        if key in seen:
            duplicate += 1
            continue
        seen.add(key)
        unlock_legal = any(getattr(action, "pattern_id", "").endswith("_hand_R_unlocks_rook_quiet")
                           for action in env.session.legal_actions())
        records.append({"rule_index": 15, "generator_seed": GENERATOR_SEED,
                        "family": family, "record": record, "record_sha256": sha(key),
                        "features": list(env.features()), "channels": [list(x) for x in env.names],
                        "same_owner": owner, "R_hand_count": hand_r,
                        "R_board_count": board_r, "promoted_P_count": promoted_p,
                        "unlock_legal_at_root": unlock_legal})
        if len(records) == ROOTS_REQUIRED:
            break

    if len(records) != ROOTS_REQUIRED:
        status.update(status="FAILED_POOL_SHORT_NO_EVALUATION", tested_families=tested,
                      selected=len(records), invalid_terminal_or_unexcited=invalid,
                      exact_history_overlaps=overlap, duplicates=duplicate,
                      elapsed_seconds=time.perf_counter() - began)
        STATUS.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise RuntimeError("fresh exact-history evaluation pool is short")

    pool = {"status": "FRESH_OUTCOME_BLIND_EVALUATION_ROOTS_PREPARED_NOT_REGISTERED",
            "candidate": {"path": RULE_REL, "index": 15, "sha256": sha(rule_raw),
                          "ruleset_fingerprint": fingerprint},
            "selection": {"generator_seed": GENERATOR_SEED,
                          "family_range": [FAMILY_RANGE.start, FAMILY_RANGE.stop],
                          "tested_families": tested, "selected": len(records),
                          "invalid_terminal_or_unexcited": invalid,
                          "prior_exact_history_rejections": overlap,
                          "within_pool_duplicates": duplicate,
                          "prior_inventory_sha256": sha(inventory_raw),
                          "old_pool_sha256": sha(old_pool_raw),
                          "additional_history_sources": source_receipts},
            "prefix_plies": PREFIX_PLIES, "evaluation_roots": records,
            "scope": "Outcome-blind exact canonical full-record exclusions and feature-conditioned roots only; no descendant/transposition/distributional independence or strength claim.",
            "registration": None, "evaluation_started": False,
            "preparation_seconds": time.perf_counter() - began}
    raw = json.dumps(pool, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    with POOL.open("xb") as stream:
        stream.write(raw)
    status.update(status="COMPLETE_PREPARED_NOT_REGISTERED", pool_sha256=sha(raw),
                  tested_families=tested, selected=len(records),
                  invalid_terminal_or_unexcited=invalid, exact_history_overlaps=overlap,
                  duplicates=duplicate, elapsed_seconds=pool["preparation_seconds"],
                  outputs_written=True)
    STATUS.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: status[key] for key in
                      ("status", "pool_sha256", "tested_families", "selected",
                       "invalid_terminal_or_unexcited", "exact_history_overlaps",
                       "duplicates", "elapsed_seconds")}, indent=2))


if __name__ == "__main__":
    main()
