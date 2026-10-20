"""Independent outcome-blind source, exact-history, and replay audit."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".local_agent/devaux_pydeps"))
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

OUT = ROOT / "results/dev_aux/task2627"
POOL = OUT / "rule15-successor-root-pools.json"
PREP_STATUS = OUT / "successor-root-preparation-status.json"
INVENTORY = OUT / "source-inventory-v2.json"
INVENTORY_BOUND_SHA = "2bcc436be65dd2001df93295bb95ae3d788755b5fd83a653bdeb9ba7c4af528f"
AUDIT = OUT / "rule15-successor-pool-audit.json"
RULE = ROOT / "results/dev_aux/task2433/rules-15.json"
TRAIN_RANGE = (140_000, 260_000)
EVAL_RANGE = (280_000, 300_000)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def walk_records(value: object):
    if isinstance(value, dict):
        if isinstance(value.get("ruleset_fingerprint"), str) and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child)


def candidate_records(path: Path, fingerprint: str):
    if path.suffix.lower() == ".jsonl":
        with path.open("rb") as stream:
            for line in stream:
                if fingerprint.encode("ascii") not in line:
                    continue
                yield from (r for r in walk_records(json.loads(line)) if r.get("ruleset_fingerprint") == fingerprint)
    else:
        yield from (r for r in walk_records(json.loads(path.read_text(encoding="utf-8")))
                    if r.get("ruleset_fingerprint") == fingerprint)


def main() -> None:
    if AUDIT.exists():
        raise FileExistsError(f"write-once audit already exists: {AUDIT}")
    pool_raw = POOL.read_bytes()
    pool = json.loads(pool_raw)
    status = json.loads(PREP_STATUS.read_text(encoding="utf-8"))
    inventory_raw = INVENTORY.read_bytes()
    inventory = json.loads(inventory_raw)
    rule_raw = RULE.read_bytes()
    candidate = pool["candidate"]
    if candidate.get("path") != "results/dev_aux/task2433/rules-15.json" or candidate.get("index") != 15:
        raise ValueError("fixed-order candidate identity mismatch")
    if sha(rule_raw) != candidate.get("sha256"):
        raise ValueError("candidate rule source hash mismatch")
    if sha(inventory_raw) != INVENTORY_BOUND_SHA or sha(inventory_raw) != pool["selection_inputs"]["dynamic_inventory_sha256"]:
        raise ValueError("dynamic inventory hash mismatch")
    if sha(pool_raw) != status.get("pool_sha256") or status.get("status") != "COMPLETE_PREPARED_NOT_REGISTERED":
        raise ValueError("preparation receipt does not bind the pool bytes")
    if status.get("training_selected") != 120 or status.get("evaluation_selected") != 16 or status.get("outputs_written") is not True:
        raise ValueError("preparation receipt counts or output state mismatch")
    if pool.get("status") != "OUTCOME_BLIND_MECHANISM_ACTIVE_ROOTS_PREPARED_NOT_REGISTERED":
        raise ValueError("pool has unexpected lifecycle status")
    if pool.get("registration") is not None or pool.get("training_started") is not None or pool.get("evaluation_started") is not None:
        raise ValueError("pool unexpectedly contains run lifecycle receipts")

    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))
    fingerprint = GameSession(compiled).to_record().ruleset_fingerprint
    if fingerprint != candidate.get("ruleset_fingerprint") or fingerprint != inventory["candidate"]["ruleset_fingerprint"]:
        raise ValueError("compiled ruleset fingerprint mismatch")

    excluded: set[bytes] = set()
    source_receipts = []
    occurrences = 0
    for source in inventory["matched_sources"]:
        path = ROOT / source["path"]
        raw_hash = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                raw_hash.update(block)
        if raw_hash.hexdigest() != source["sha256"]:
            raise ValueError(f"history source hash changed: {source['path']}")
        found = list(candidate_records(path, fingerprint))
        if len(found) != source["record_occurrences"]:
            raise ValueError(f"history occurrence count changed: {source['path']}")
        source_unique = {canon(record) for record in found}
        if len(source_unique) != source["unique_records_in_file"]:
            raise ValueError(f"per-file unique count changed: {source['path']}")
        excluded.update(source_unique)
        occurrences += len(found)
        source_receipts.append({"path": source["path"], "sha256": raw_hash.hexdigest(),
                                "occurrences": len(found), "unique_records": len(source_unique)})
    excluded_hashes = sorted(sha(item) for item in excluded)
    if occurrences != inventory["exact_candidate_record_occurrences"]:
        raise ValueError("dynamic inventory total occurrence count mismatch")
    if len(excluded) != inventory["unique_exact_candidate_records"] or excluded_hashes != inventory["unique_record_sha256"]:
        raise ValueError("reconstructed exact-history set differs from inventory")
    if inventory["matched_compressed_sources"]:
        raise ValueError("compressed exact-history sources require explicit audited support")

    prefit_path = ROOT / "results/dev_aux/task2433/inputs.json"
    prefit_raw = prefit_path.read_bytes()
    prefit = json.loads(prefit_raw)
    prefit_records = [row["record"] for row in prefit
                      if row["record"].get("ruleset_fingerprint") == fingerprint]
    excluded.update(canon(record) for record in prefit_records)
    witness_path = ROOT / "results/dev_aux/task2626/task2433-unvisited-variant-screen.json"
    witness_raw = witness_path.read_bytes()
    witness_data = json.loads(witness_raw)
    witness = next(row for row in witness_data["records"] if row["index"] == 15)["witness"]["record"]
    if witness.get("ruleset_fingerprint") != fingerprint:
        raise ValueError("saved mechanism witness rule mismatch")
    excluded.add(canon(witness))

    split_keys: dict[str, set[bytes]] = {}
    totals = Counter()
    unlock_available = {}
    for name, rows, count, family_range in (
        ("training", pool["training_roots"], 120, TRAIN_RANGE),
        ("evaluation", pool["evaluation_roots"], 16, EVAL_RANGE),
    ):
        meta = pool[name]
        if meta.get("family_range") != list(family_range) or meta.get("selected") != count or len(rows) != count:
            raise ValueError(f"{name} root count/range metadata mismatch")
        local: set[bytes] = set()
        families: set[int] = set()
        available: list[int] = []
        for row in rows:
            record = row["record"]
            encoded = canon(record)
            family = row.get("family")
            if row.get("rule_index") != 15 or row.get("generator_seed") != 2_433_017:
                raise ValueError(f"{name} fixed rule index or seed mismatch")
            if type(family) is not int or not family_range[0] <= family < family_range[1] or family in families:
                raise ValueError(f"{name} family identity/range violation")
            families.add(family)
            if record.get("ruleset_fingerprint") != fingerprint or sha(encoded) != row.get("record_sha256"):
                raise ValueError(f"{name} candidate record fingerprint/hash mismatch")
            if encoded in excluded:
                raise ValueError(f"{name} root intersects exact prior history")
            if encoded in local:
                raise ValueError(f"{name} contains duplicate exact roots")
            typed = deserialize_game_record(json.dumps(record))
            session = GameSession.replay(compiled, typed)
            env = FixedScaleSessionEnv(session)
            if session.to_record() != typed or len(record.get("actions", [])) != 8 or env.terminal() is not None:
                raise ValueError(f"{name} root full-history replay/terminal check failed")
            if list(env.features()) != row["features"] or [list(x) for x in env.names] != row["channels"]:
                raise ValueError(f"{name} fixed-scale feature receipt mismatch")
            owner = row["same_owner"]
            position = session.state.position
            hand_r = sum(n for base, n in position.hands[owner].counts if base == "R")
            board_r = sum(1 for piece in position.board if piece is not None and piece.owner == owner and piece.current_type_id == "R")
            promoted_p = sum(1 for piece in position.board if piece is not None and piece.owner == owner
                             and piece.base_type_id == "P" and piece.current_type_id == "R")
            if (hand_r, board_r, promoted_p) != (row["R_hand_count"], row["R_board_count"], row["promoted_P_count"]):
                raise ValueError(f"{name} same-owner mechanism counts mismatch")
            if min(hand_r, board_r, promoted_p) < 1:
                raise ValueError(f"{name} root lacks required active features")
            if any(getattr(action, "pattern_id", "").endswith("_hand_R_unlocks_rook_quiet")
                   for action in session.legal_actions()):
                available.append(family)
            local.add(encoded)
            totals.update({"R_hand_roots": 1, "R_board_roots": 1, "promoted_P_roots": 1,
                           "R_hand_pieces": hand_r, "R_board_pieces": board_r, "promoted_P_pieces": promoted_p})
        split_keys[name] = local
        unlock_available[name] = {"roots_with_legal_unlock_action": len(available), "sample_families": available[:8]}

    overlap = split_keys["training"] & split_keys["evaluation"]
    if overlap or pool.get("exact_train_evaluation_overlap") != 0:
        raise ValueError("training/evaluation exact-record overlap")
    audit = {
        "status": "PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT",
        "pool_sha256": sha(pool_raw),
        "preparation_script_sha256": sha((OUT / "prepare_rule15_successor_roots.py").read_bytes()),
        "audit_script_sha256": sha(Path(__file__).read_bytes()),
        "candidate_rule_sha256": sha(rule_raw),
        "candidate_fingerprint": fingerprint,
        "inventory_sha256": sha(inventory_raw),
        "inventory_unique_prior_histories": inventory["unique_exact_candidate_records"],
        "inventory_occurrences": occurrences,
        "prefit_candidate_histories": len(prefit_records),
        "prior_unique_with_prefit_and_witness": len(excluded),
        "verified_history_sources": source_receipts,
        "training_roots": len(split_keys["training"]),
        "evaluation_roots": len(split_keys["evaluation"]),
        "exact_prior_intersections": 0,
        "exact_training_evaluation_intersections": len(overlap),
        "full_history_replayed_roots": sum(map(len, split_keys.values())),
        "mechanism_feature_totals": dict(totals),
        "legal_unlock_action_availability": unlock_available,
        "preparation_seconds": pool["preparation_seconds"],
        "scope": "Exact canonical full-record exclusions and deterministic full-history replay only; no descendant, transposition, distributional-independence, learning or strength claim.",
        "registration_training_evaluation_started": False,
    }
    AUDIT.write_bytes(json.dumps(audit, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n")
    print(json.dumps({k: v for k, v in audit.items() if k != "verified_history_sources"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
