"""Independent source/history/replay audit for task2629 evaluation roots."""
from __future__ import annotations

import hashlib
import json
import sys
import time
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

OUT = ROOT / "results/dev_aux/task2629"
POOL_PATH = OUT / "fresh-evaluation-roots.json"
STATUS_PATH = OUT / "root-preparation-status.json"
INVENTORY = ROOT / "results/dev_aux/task2627/source-inventory-v2.json"
OLD_POOL = ROOT / "results/dev_aux/task2627/rule15-successor-root-pools.json"
TASK2628_RUN = ROOT / "results/dev_aux/task2628/run"
RULE = ROOT / "results/dev_aux/task2433/rules-15.json"
AUDIT_PATH = OUT / "fresh-evaluation-root-audit.json"
AUDIT_CAP_SECONDS = 180.0


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


def iter_records(path: Path, fingerprint: str):
    needle = fingerprint.encode("ascii")
    if path.suffix.lower() == ".jsonl":
        with path.open("rb") as stream:
            for line in stream:
                if needle in line:
                    yield from (r for r in walk_records(json.loads(line))
                                if r.get("ruleset_fingerprint") == fingerprint)
    else:
        raw = path.read_bytes()
        if needle in raw:
            yield from (r for r in walk_records(json.loads(raw))
                        if r.get("ruleset_fingerprint") == fingerprint)


def main() -> None:
    if AUDIT_PATH.exists():
        raise FileExistsError("task2629 root audit is write-once")
    began = time.perf_counter()
    pool_raw = POOL_PATH.read_bytes()
    pool = json.loads(pool_raw)
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    rule_raw = RULE.read_bytes()
    inventory_raw = INVENTORY.read_bytes()
    inventory = json.loads(inventory_raw)
    old_pool_raw = OLD_POOL.read_bytes()
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))
    fingerprint = GameSession(compiled).to_record().ruleset_fingerprint
    if (pool.get("status") != "FRESH_OUTCOME_BLIND_EVALUATION_ROOTS_PREPARED_NOT_REGISTERED"
            or status.get("status") != "COMPLETE_PREPARED_NOT_REGISTERED"
            or status.get("pool_sha256") != sha(pool_raw)
            or pool.get("registration") is not None or pool.get("evaluation_started") is not False):
        raise ValueError("pool lifecycle receipt mismatch")
    if (pool["candidate"]["sha256"] != sha(rule_raw)
            or pool["candidate"]["ruleset_fingerprint"] != fingerprint
            or inventory["candidate"]["ruleset_fingerprint"] != fingerprint):
        raise ValueError("candidate rule/fingerprint mismatch")
    if pool["selection"]["prior_inventory_sha256"] != sha(inventory_raw):
        raise ValueError("prior history inventory binding mismatch")
    if pool["selection"]["old_pool_sha256"] != sha(old_pool_raw):
        raise ValueError("old root pool binding mismatch")

    excluded: set[bytes] = set()
    source_receipts = []
    for source in inventory["matched_sources"]:
        if time.perf_counter() - began > AUDIT_CAP_SECONDS:
            raise TimeoutError("root audit cap reached before audit output")
        path = ROOT / source["path"]
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != source["sha256"]:
            raise ValueError(f"pinned historical source changed: {source['path']}")
        found = list(iter_records(path, fingerprint))
        unique = {canon(record) for record in found}
        if (len(found) != source["record_occurrences"]
                or len(unique) != source["unique_records_in_file"]):
            raise ValueError(f"history occurrence/unique count mismatch: {source['path']}")
        excluded.update(unique)
        source_receipts.append({"path": source["path"], "sha256": h.hexdigest(),
                                "occurrences": len(found), "unique": len(unique)})
    if sorted(sha(item) for item in excluded) != inventory["unique_record_sha256"]:
        raise ValueError("prior inventory reconstructed to different histories")

    old_pool = json.loads(old_pool_raw)
    old_keys = {canon(record) for record in walk_records(old_pool)
                if record.get("ruleset_fingerprint") == fingerprint}
    excluded.update(old_keys)
    current_paths = [TASK2628_RUN / name for name in
                     ("queries.jsonl", "episodes.jsonl", "eval-queries.jsonl", "eval-games.jsonl")]
    current_unique = {}
    for path in current_paths:
        h = hashlib.sha256()
        unique = set()
        with path.open("rb") as stream:
            for line in stream:
                h.update(line)
                if fingerprint.encode("ascii") not in line:
                    continue
                row = json.loads(line)
                unique.update(canon(record) for record in walk_records(row)
                              if record.get("ruleset_fingerprint") == fingerprint)
        receipt = next((x for x in pool["selection"]["additional_history_sources"]
                        if x["path"] == path.relative_to(ROOT).as_posix()), None)
        if receipt is None or receipt["sha256"] != h.hexdigest() or receipt["unique"] != len(unique):
            raise ValueError(f"task2628 history source receipt mismatch: {path.name}")
        current_unique[path.name] = len(unique)
        excluded.update(unique)

    roots = pool.get("evaluation_roots", [])
    if len(roots) != 16:
        raise ValueError("fresh evaluation root count is not 16")
    local: set[bytes] = set()
    families: set[int] = set()
    counts = Counter()
    for row in roots:
        rec = row["record"]
        key = canon(rec)
        family = row.get("family")
        if (row.get("rule_index") != 15 or row.get("generator_seed") != pool["selection"]["generator_seed"]
                or not isinstance(family, int) or family not in range(*pool["selection"]["family_range"])):
            raise ValueError("root rule/seed/family identity mismatch")
        if family in families or key in local or key in excluded:
            raise ValueError("duplicate or exact-history-overlapping root")
        if rec.get("ruleset_fingerprint") != fingerprint or sha(key) != row.get("record_sha256"):
            raise ValueError("root record hash/fingerprint mismatch")
        record = deserialize_game_record(json.dumps(rec))
        session = GameSession.replay(compiled, record)
        env = FixedScaleSessionEnv(session)
        if (session.to_record() != record or len(record.actions) != 8 or env.terminal() is not None
                or list(env.features()) != row["features"]
                or [list(x) for x in env.names] != row["channels"]):
            raise ValueError("full history, terminal or feature replay failed")
        owner = row["same_owner"]
        position = session.state.position
        hand_r = sum(n for base, n in position.hands[owner].counts if base == "R")
        board_r = sum(1 for piece in position.board if piece is not None and piece.owner == owner
                      and piece.current_type_id == "R")
        promoted_p = sum(1 for piece in position.board if piece is not None and piece.owner == owner
                         and piece.base_type_id == "P" and piece.current_type_id == "R")
        unlock = any(getattr(action, "pattern_id", "").endswith("_hand_R_unlocks_rook_quiet")
                     for action in session.legal_actions())
        if ((hand_r, board_r, promoted_p) !=
                (row["R_hand_count"], row["R_board_count"], row["promoted_P_count"])
                or min(hand_r, board_r, promoted_p) < 1
                or unlock != row["unlock_legal_at_root"]):
            raise ValueError("mechanism counts/action availability replay failed")
        families.add(family)
        local.add(key)
        counts.update(R_hand=1, R_board=1, promoted_P=1, unlock_available=int(unlock))

    audit = {"status": "PASS_FRESH_EVALUATION_POOL_EXACT_HISTORY_AND_REPLAY_AUDIT",
             "pool_sha256": sha(pool_raw), "preparation_script_sha256": sha((OUT / "prepare_fresh_eval_roots.py").read_bytes()),
             "audit_script_sha256": sha(Path(__file__).read_bytes()),
             "rule_sha256": sha(rule_raw), "prior_inventory_sha256": sha(inventory_raw),
             "old_pool_sha256": sha(old_pool_raw), "prior_unique_inventory_records": len(inventory["unique_record_sha256"]),
             "old_pool_unique_records": len(old_keys), "task2628_unique_records_by_source": current_unique,
             "verified_inventory_sources": len(source_receipts), "roots": len(local),
             "exact_prior_intersections": 0, "duplicate_roots": 0,
             "legal_unlock_action_roots": counts["unlock_available"],
             "preparation_seconds": pool["preparation_seconds"],
             "audit_seconds": time.perf_counter() - began,
             "scope": "Exact canonical full-record exclusion from the pinned history inventory, prior panel, and task2628 trajectories; full replay/feature/action checks. No descendant/transposition/distributional independence or strength claim."}
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "verified_inventory_sources"}, indent=2))


if __name__ == "__main__":
    main()
