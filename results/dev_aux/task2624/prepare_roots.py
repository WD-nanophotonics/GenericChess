"""Outcome-blind, exact-history-disjoint root pools for task2624.

The selector reads only complete GameSession records from prior inputs and
newly generated prefixes. It never uses outcomes, scores, weights, PVs, or
post-root actions for acceptance. This is preparation, not registration or a
strength run.
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
from results.dev_aux.task2606.train import environment, prefix
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from tools.local_agent.environment import require_identity

OUT = ROOT / "results/dev_aux/task2624"
RULES = (271001, 271002, 271003, 271004)
TRAIN_RANGE = range(3_000_000, 3_100_000)
EVAL_RANGE = range(4_000_000, 4_100_000)
GENERATOR_SEED = 0
PREFIX_PLIES = 8
TRAIN_PER_RULE = 120
EVAL_PER_RULE = 16

# Enumerated from prior Generic registrations and the current task2621 probe.
# Records are extracted from these fixed evidence streams; no result labels are
# consulted. Empty/failed registered streams remain included where present.
HISTORY_FILES = (
    "results/dev_aux/task2525/queries.jsonl",
    "results/dev_aux/task2525/episodes.jsonl",
    "results/dev_aux/task2565/generic/queries.jsonl",
    "results/dev_aux/task2565/generic/games.jsonl",
    "results/dev_aux/task2565/generic/eval-queries.jsonl",
    "results/dev_aux/task2565/generic/eval-games.jsonl",
    "results/dev_aux/task2606/queries.jsonl",
    "results/dev_aux/task2606/games.jsonl",
    "results/dev_aux/task2606/eval-queries.jsonl",
    "results/dev_aux/task2606/eval-games.jsonl",
    "results/dev_aux/task2608/eval-queries.jsonl",
    "results/dev_aux/task2608/eval-games.jsonl",
    "results/dev_aux/task2609/eval-queries.jsonl",
    "results/dev_aux/task2609/eval-games.jsonl",
    "results/dev_aux/task2610/eval-queries.jsonl",
    "results/dev_aux/task2610/eval-games.jsonl",
    "results/dev_aux/task2610/attempt-2/eval-queries.jsonl",
    "results/dev_aux/task2610/attempt-2/eval-games.jsonl",
    "results/dev_aux/task2621/active-feature-probe/queries.jsonl",
    "results/dev_aux/task2621/cost-scan/queries.jsonl",
    "results/dev_aux/task2621/cost-scan/episodes.jsonl",
    "results/dev_aux/task2622/run/queries.jsonl",
    "results/dev_aux/task2622/run/episodes.jsonl",
    "results/dev_aux/task2623/run/queries.jsonl",
    "results/dev_aux/task2623/run/episodes.jsonl",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def record_key(record: dict) -> bytes:
    return canonical(record)


def record_fields(row: dict):
    # These are the only row fields used by selection. Labels, search values,
    # model parameters, and post-root actions are not referenced.
    for key in ("record_before", "record_after", "initial_record", "final_record", "record"):
        record = row.get(key)
        if isinstance(record, dict):
            yield record


def walk_records(value):
    """Yield complete record objects from manifests without reading labels."""
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
    if (OUT / "root-pools-v2.json").exists():
        raise FileExistsError("task2624 preparation is write-once; preserve it and use a new revision")
    OUT.mkdir(parents=True, exist_ok=True)
    began = time.perf_counter()

    root_manifest = json.loads((ROOT / "results/dev_aux/task2609/root-manifest.json").read_text(encoding="utf-8"))
    fingerprints = {}
    for key, record in root_manifest["roots"].items():
        rule = int(key.split(":", 1)[0])
        fingerprint = record["ruleset_fingerprint"]
        if rule in RULES:
            if fingerprint in fingerprints and fingerprints[fingerprint] != rule:
                raise ValueError("ruleset fingerprint collision across registered rule IDs")
            fingerprints[fingerprint] = rule
    if set(fingerprints.values()) != set(RULES):
        raise ValueError("task2609 does not bind all four frozen Generic rule fingerprints")

    histories = {rule: set() for rule in RULES}
    file_receipts = []
    for relative in HISTORY_FILES:
        path = ROOT / relative
        if not path.is_file():
            file_receipts.append({"path": relative, "status": "MISSING", "rows": 0})
            continue
        raw_hash = hashlib.sha256()
        rows = matched = 0
        with path.open("rb") as stream:
            for raw_line in stream:
                raw_hash.update(raw_line)
                if not raw_line.strip():
                    continue
                rows += 1
                row = json.loads(raw_line)
                for record in record_fields(row):
                    rule = fingerprints.get(record.get("ruleset_fingerprint"))
                    if rule is not None:
                        histories[rule].add(record_key(record))
                        matched += 1
        file_receipts.append({"path": relative, "status": "READ", "bytes": path.stat().st_size,
                              "sha256": raw_hash.hexdigest(), "rows": rows,
                              "target_record_occurrences": matched})

    # Root manifests can expose starts with no query (for example a registered
    # but never-launched panel). Scan all role evidence manifests, including the
    # first task2622 preparation: those v1 roots are now development-exposed.
    root_manifest_paths = sorted({
        *ROOT.joinpath("results/dev_aux").rglob("root-manifest.json"),
        *ROOT.joinpath("results/dev_aux").rglob("root-candidates.json"),
        ROOT / "results/dev_aux/task2622/root-pools.json",
        ROOT / "results/dev_aux/task2622/root-pools-v2.json",
    })
    for path in root_manifest_paths:
        if not path.is_file():
            continue
        raw = path.read_bytes()
        doc = json.loads(raw)
        matches = 0
        for record in walk_records(doc):
            rule = fingerprints.get(record.get("ruleset_fingerprint"))
            if rule is not None:
                histories[rule].add(record_key(record))
                matches += 1
        file_receipts.append({"path": path.relative_to(ROOT).as_posix(), "status": "READ_JSON_RECORDS_ONLY",
                              "bytes": len(raw), "sha256": sha(raw),
                              "target_record_occurrences": matches})

    compiled = {}
    rule_pins = {}
    for rule in RULES:
        rule_path = ROOT / f"results/dev_aux/task2525/rules-{rule}.json"
        raw = rule_path.read_bytes()
        rule_pins[rule_path.relative_to(ROOT).as_posix()] = sha(raw)
        compiled[rule] = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))

    def candidate(rule: int, family: int):
        env = FixedScaleSessionEnv(GameSession(compiled[rule]))
        prefix(env, rule, family, PREFIX_PLIES)
        record = env.record()
        if len(record.get("actions", ())) != PREFIX_PLIES or env.terminal() is not None:
            return None
        features = env.features()
        # Retain the active-feature criterion from task2621, fixed before any
        # new search or outcome: at least one non-unit board/hand channel.
        if not any(features[1:]):
            return None
        env.replay()
        return record, list(features), [list(x) for x in env.names]

    def select(pool: range, amount: int, excluded: set[bytes], within: set[bytes], label: str):
        selected = []
        examined = invalid = duplicate = overlap = inactive = 0
        for family in pool:
            for rule in RULES:
                if sum(row["rule"] == rule for row in selected) >= amount:
                    continue
                generated = candidate(rule, family)
                examined += 1
                if generated is None:
                    invalid += 1
                    continue
                record, features, channels = generated
                key = record_key(record)
                if key in excluded:
                    overlap += 1
                    continue
                if key in within:
                    duplicate += 1
                    continue
                within.add(key)
                selected.append({"rule": rule, "generator_seed": GENERATOR_SEED,
                                 "family": family, "record": record,
                                 "record_sha256": sha(key), "features": features,
                                 "channels": channels})
            if all(sum(row["rule"] == rule for row in selected) >= amount for rule in RULES):
                break
        counts = {rule: sum(row["rule"] == rule for row in selected) for rule in RULES}
        if counts != {rule: amount for rule in RULES}:
            raise RuntimeError(f"{label} pool shortage under fixed family range: {counts}")
        return selected, {"candidate_family_range": [pool.start, pool.stop],
                          "family_scan_seed": GENERATOR_SEED, "prefix_plies": PREFIX_PLIES,
                          "selected_per_rule": amount, "selected": len(selected),
                          "examined_rule_family_pairs": examined, "invalid_or_inactive": invalid,
                          "exact_prior_overlap_rejections": overlap,
                          "within_pool_exact_duplicate_rejections": duplicate,
                          "selected_rule_counts": counts}

    prior = set().union(*histories.values())
    train, train_stats = select(TRAIN_RANGE, TRAIN_PER_RULE, prior, set(), "training")
    train_keys = {record_key(row["record"]) for row in train}
    evaluation, eval_stats = select(EVAL_RANGE, EVAL_PER_RULE, prior | train_keys, set(), "evaluation")

    train_by_rule = {rule: {record_key(row["record"]) for row in train if row["rule"] == rule} for rule in RULES}
    eval_by_rule = {rule: {record_key(row["record"]) for row in evaluation if row["rule"] == rule} for rule in RULES}
    if any(train_by_rule[r] & eval_by_rule[r] for r in RULES):
        raise AssertionError("exact full-history train/evaluation overlap")

    result = {
        "status": "OUTCOME_BLIND_EXACT_HISTORY_ROOT_POOLS_PREPARED_NOT_REGISTERED",
        "scope": "Four frozen development Generic rules 271001-271004; not unfamiliar-rule/full-domain generalization.",
        "root_identity": "Canonical complete GameSession JSON, including ruleset fingerprint and ordered full action history.",
        "selection_inputs": {"history_files": file_receipts, "rule_sha256": rule_pins,
                             "prior_unique_full_histories_by_rule": {r: len(histories[r]) for r in RULES}},
        "selection_policy": "First eligible 8-ply nonterminal roots in ascending family order; exact prior-history matches and within-pool duplicates rejected; require a nonzero non-unit inventory feature; no outcomes/search/model values used.",
        "training": train_stats,
        "evaluation": eval_stats,
        "training_roots": train,
        "evaluation_roots": evaluation,
        "exact_train_eval_overlap_by_rule": {r: len(train_by_rule[r] & eval_by_rule[r]) for r in RULES},
        "limitations": [
            "Exact record exclusion covers only the enumerated prior Generic evidence streams and observed decision histories; it does not cover unvisited interior search nodes or unknown historical roots.",
            "Exact start-history disjointness is not transposition, semantic-state, or distributional independence.",
            "The selected roots are now development-exposed; bind and publish their hashes before any learner or evaluation outcomes are run.",
            "No registration, training, fitness search, or strength claim is created by this preparation.",
        ],
        "preparation_seconds": time.perf_counter() - began,
    }
    raw = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    (OUT / "root-pools-v2.json").write_bytes(raw)
    print(json.dumps({"status": result["status"], "training": train_stats,
                      "evaluation": eval_stats, "prior_unique_full_histories_by_rule": result["selection_inputs"]["prior_unique_full_histories_by_rule"],
                      "preparation_seconds": result["preparation_seconds"],
                      "root_pools_sha256": sha(raw)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
