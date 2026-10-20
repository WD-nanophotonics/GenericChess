"""Outcome-blind, write-once root preparation for task2433 rules-0.

Only complete GameSession records and rule-derived feature excitation are
read for selection. No terminal labels, search targets, model values, or query
scores are opened or used.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity

OUT = ROOT / "results/dev_aux/task2626"
RULE_PATH = ROOT / "results/dev_aux/task2433/rules-0.json"
RULE_REL = RULE_PATH.relative_to(ROOT).as_posix()
TRAIN_RANGE = range(3_200_000, 3_300_000)
EVAL_RANGE = range(4_200_000, 4_300_000)
PREFIX_PLIES = 8
TRAIN_N = 120
EVAL_N = 16
SEED_RULE = 2433 * 1000  # fixed candidate identity, not an outcome-dependent seed
HISTORY_FILES = (
    "results/dev_aux/task2433/inputs.jsonl",
    "results/dev_aux/task2525/queries.jsonl", "results/dev_aux/task2525/episodes.jsonl",
    "results/dev_aux/task2565/generic/queries.jsonl", "results/dev_aux/task2565/generic/games.jsonl",
    "results/dev_aux/task2565/generic/eval-queries.jsonl", "results/dev_aux/task2565/generic/eval-games.jsonl",
    "results/dev_aux/task2606/queries.jsonl", "results/dev_aux/task2606/games.jsonl",
    "results/dev_aux/task2606/eval-queries.jsonl", "results/dev_aux/task2606/eval-games.jsonl",
    "results/dev_aux/task2608/eval-queries.jsonl", "results/dev_aux/task2608/eval-games.jsonl",
    "results/dev_aux/task2609/eval-queries.jsonl", "results/dev_aux/task2609/eval-games.jsonl",
    "results/dev_aux/task2610/eval-queries.jsonl", "results/dev_aux/task2610/eval-games.jsonl",
    "results/dev_aux/task2610/attempt-2/eval-queries.jsonl", "results/dev_aux/task2610/attempt-2/eval-games.jsonl",
    "results/dev_aux/task2618/learner-comparison-v2/queries.jsonl",
    "results/dev_aux/task2618/learner-comparison-v2/games.jsonl",
    "results/dev_aux/task2618/learner-comparison-v3/queries.jsonl",
    "results/dev_aux/task2618/learner-comparison-v3/games.jsonl",
    "results/dev_aux/task2621/active-feature-probe/queries.jsonl",
    "results/dev_aux/task2621/cost-scan/queries.jsonl", "results/dev_aux/task2621/cost-scan/episodes.jsonl",
    "results/dev_aux/task2622/run/queries.jsonl", "results/dev_aux/task2622/run/episodes.jsonl",
    "results/dev_aux/task2623/run/queries.jsonl", "results/dev_aux/task2623/run/episodes.jsonl",
    "results/dev_aux/task2625/run/queries.jsonl", "results/dev_aux/task2625/run/episodes.jsonl",
    "results/dev_aux/task2625/run/eval-queries.jsonl", "results/dev_aux/task2625/run/eval-games.jsonl",
)
ROOT_MANIFESTS = (
    "results/dev_aux/task2607/root-candidates.json",
    "results/dev_aux/task2609/root-manifest.json",
    "results/dev_aux/task2610/root-manifest.json",
    "results/dev_aux/task2622/root-pools.json",
    "results/dev_aux/task2622/root-pools-v2.json",
    "results/dev_aux/task2624/root-pools-v2.json",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def record_key(record: dict) -> bytes:
    return canonical(record)


def row_records(row: dict):
    for key in ("record_before", "record_after", "initial_record", "final_record", "record"):
        record = row.get(key)
        if isinstance(record, dict):
            yield record


def walk_records(value):
    if isinstance(value, dict):
        if isinstance(value.get("ruleset_fingerprint"), str) and isinstance(value.get("actions"), list):
            yield value
        for child in value.values():
            yield from walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_records(child)


def main() -> None:
    require_identity()
    pool_path = OUT / "root-pools.json"
    OUT.mkdir(parents=True, exist_ok=True)
    if pool_path.exists():
        raise FileExistsError("task2626 root-pools.json is write-once; preserve it and choose a new task")
    began = time.perf_counter()
    raw_rule = RULE_PATH.read_bytes()
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw_rule)))
    initial = GameSession(compiled)
    fingerprint = initial.to_record().ruleset_fingerprint

    # Candidate-specific search/query logs are included by fingerprint. Saved
    # task2433 pre-fit inputs are included for all 16 rules; task2411 controls
    # are separately inventoried and their complete histories are preserved.
    histories: set[bytes] = set()
    receipts = []
    matching_occurrences = 0
    for relative in HISTORY_FILES:
        path = ROOT / relative
        if not path.is_file():
            receipts.append({"path": relative, "status": "MISSING", "candidate_record_occurrences": 0})
            continue
        h = hashlib.sha256(); rows = occ = 0
        with path.open("rb") as stream:
            for line in stream:
                h.update(line)
                if not line.strip(): continue
                rows += 1
                try: row = json.loads(line)
                except json.JSONDecodeError: continue
                for record in row_records(row):
                    if record.get("ruleset_fingerprint") == fingerprint:
                        histories.add(record_key(record)); occ += 1
        receipts.append({"path": relative, "status": "READ", "sha256": h.hexdigest(),
                         "bytes": path.stat().st_size, "rows": rows,
                         "candidate_record_occurrences": occ})
        matching_occurrences += occ

    for relative in ROOT_MANIFESTS:
        path = ROOT / relative
        if not path.is_file():
            receipts.append({"path": relative, "status": "MISSING", "candidate_record_occurrences": 0})
            continue
        raw = path.read_bytes(); doc = json.loads(raw); occ = 0
        for record in walk_records(doc):
            if record.get("ruleset_fingerprint") == fingerprint:
                histories.add(record_key(record)); occ += 1
        if occ:
            receipts.append({"path": relative, "status": "READ_JSON_RECORDS_ONLY", "sha256": sha(raw),
                             "bytes": len(raw), "candidate_record_occurrences": occ,
                             "mode": "complete_record_objects_only"})
            matching_occurrences += occ

    # Fixed-order task2433 roots are direct exposure, irrespective of fitness
    # queries. Include all records, then key by exact candidate fingerprint.
    prefit_raw = (ROOT / "results/dev_aux/task2433/inputs.json").read_bytes()
    prefit = json.loads(prefit_raw)
    task2433_occ = 0
    for row in prefit:
        rec = row["record"]
        if rec.get("ruleset_fingerprint") == fingerprint:
            histories.add(record_key(rec)); task2433_occ += 1
    receipts.append({"path": "results/dev_aux/task2433/inputs.json", "sha256": sha(prefit_raw),
                     "bytes": len(prefit_raw), "candidate_record_occurrences": task2433_occ,
                     "mode": "all_saved_prefit_roots_including_reserve"})

    # Task2411 is a distinct ruleset control. Its records cannot be an exact
    # candidate full-history match because full records bind rule fingerprints;
    # retain receipts for explicit cross-rule exposure accounting.
    control_raw = (ROOT / "results/dev_aux/task2411/inputs.json").read_bytes()
    controls = json.loads(control_raw)
    control_records = [r["record"] for r in controls]
    control_fingerprints = sorted({r.get("ruleset_fingerprint") for r in control_records})

    def make_candidate(family: int):
        env = FixedScaleSessionEnv(GameSession(compiled))
        prefix(env, SEED_RULE, family, PREFIX_PLIES)
        record = env.record()
        if len(record.get("actions", ())) != PREFIX_PLIES or env.terminal() is not None:
            return None
        env.replay()
        position = env.session.state.position
        # Preserve both decision-relevant channels in the root: a real R in
        # hand and a live base P on board. Promotion itself is sparse and is
        # audited on continuations/cost feasibility rather than falsely
        # required in the 8-ply roots (the capped probe saw none).
        r_hand = sum(count for hand in position.hands for base, count in hand.counts if base == "R")
        pawn = [p for p in position.board if p is not None and
                p.base_type_id == "P" and p.current_type_id == "P"]
        features = list(env.features())
        return record, features, [list(x) for x in env.names], r_hand, len(pawn)

    def select(families: range, count: int, excluded: set[bytes], label: str):
        selected = []; examined = invalid = overlap = duplicate = 0
        feature_reject = {"no_R_hand": 0, "no_live_P_on_board": 0}
        seen = set()
        for family in families:
            item = make_candidate(family); examined += 1
            if item is None:
                invalid += 1; continue
            record, features, channels, r_hand, promoted_n = item
            key = record_key(record)
            if key in excluded:
                overlap += 1; continue
            if key in seen:
                duplicate += 1; continue
            if not r_hand:
                feature_reject["no_R_hand"] += 1; continue
            if not promoted_n:
                feature_reject["no_live_P_on_board"] += 1; continue
            seen.add(key)
            selected.append({"rule": "task2433-rules-0", "generator_seed": SEED_RULE,
                             "family": family, "record": record, "record_sha256": sha(key),
                             "features": features, "channels": channels,
                             "active_R_hand_count": r_hand, "live_P_on_board_count": promoted_n})
            if len(selected) == count:
                break
        if len(selected) != count:
            raise RuntimeError(f"{label} pool shortage: selected={len(selected)}, required={count}, "
                               f"examined={examined}, feature_rejections={feature_reject}")
        return selected, {"family_range": [families.start, families.stop], "selected": len(selected),
                          "examined": examined, "invalid_or_terminal": invalid,
                          "exact_prior_history_rejections": overlap,
                          "within_pool_duplicate_rejections": duplicate,
                          "feature_rejections": feature_reject}

    training, train_stats = select(TRAIN_RANGE, TRAIN_N, histories, "training")
    train_keys = {record_key(row["record"]) for row in training}
    evaluation, eval_stats = select(EVAL_RANGE, EVAL_N, histories | train_keys, "evaluation")
    result = {
        "status": "OUTCOME_BLIND_EXACT_HISTORY_ROOT_POOL_PREPARED_NOT_REGISTERED",
        "scope": "One fixed-order existing generated task2433 rules-0 candidate; no full-domain or population claim.",
        "candidate": {"path": RULE_REL, "sha256": sha(raw_rule), "ruleset_fingerprint": fingerprint,
                      "task2433_prefit_roots": len(prefit), "candidate_prefit_matches": task2433_occ,
                      "saved_task2433_fitness_queries": 0},
        "selection_inputs": {"history_sources": receipts,
                             "prior_unique_candidate_histories": len(histories),
                             "candidate_record_occurrences": matching_occurrences + task2433_occ,
                             "task2411_control": {"path": "results/dev_aux/task2411/inputs.json",
                                "sha256": sha(control_raw), "records": len(control_records),
                                "fingerprints": control_fingerprints,
                                "cross_rule_exact_candidate_matches": sum(
                                    1 for r in control_records if record_key(r) in histories)}},
        "selection_policy": "First fixed-family-order 8-ply ongoing exact GameSession histories; exclude all prior exact candidate records; require both an R in hand and a live P on board so both corresponding feature channels are active; no outcome, search, weight, or query label used. The root panel does not claim any P-to-R promotion occurred; continuations need a separate exposure check.",
        "training": train_stats, "evaluation": eval_stats,
        "exact_training_evaluation_overlap": 0,
        "training_roots": training, "evaluation_roots": evaluation,
        "limitations": [
            "Exact-record exclusion covers enumerated project JSONL/manifests and saved task2433/task2411 input roots; it does not cover semantic transpositions, unknown sources, descendant states, or distributional independence.",
            "task2411 has a distinct ruleset fingerprint and is recorded as a control exposure, not pooled as the same candidate rule.",
            "R-hand and live-P channel excitation is required at roots. A capped scan of 10,000 eight-ply roots observed zero promoted pieces, so actual P-to-R trajectory frequency must be measured in source-matched feasibility before any training registration.",
            "Preparation creates no registration, learner update, fitness query, strength result, or test of complete Generic-domain transfer."
        ],
        "preparation_seconds": time.perf_counter() - began,
    }
    raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    with pool_path.open("xb") as out:
        out.write(raw)
    print(json.dumps({"status": result["status"], "training": train_stats, "evaluation": eval_stats,
                      "prior_unique_candidate_histories": len(histories),
                      "preparation_seconds": result["preparation_seconds"],
                      "root_pools_sha256": sha(raw)}, indent=2))


if __name__ == "__main__":
    main()
