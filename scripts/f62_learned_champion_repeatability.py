"""F62 exact-mechanism repeatability: learned Gen1 -> learned Gen2.

The experiment freezes the successful F61 D0 mechanism, changes only the
parent/teacher and fresh deterministic data, checkpoints every expensive unit,
and gives actual equal-budget parent/child play sole strength authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena_resumable  # noqa: E402
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f60_disjoint_policy_objective_validation as f60  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


WORK_ORDER = "GENERICCHESS-F62-LEARNED-CHAMPION-REPEATABILITY"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f62_results.json"
PARTIAL_PATH = OUT / "f62_partial.json"
GEN2_PATH = OUT / "gen2_checkpoint.json"
STAGE_MANIFEST_PATH = PROGRESS / "stage-manifest.json"
MODEL_PARAMS = ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"

GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
GEN1_CANDIDATE = "F60_D0_PAIRWISE_SEED_59012"
TRAINING_SEED = 59012
DATA_OPENING_SEED = 630101
DATA_CORPUS_SEED = 630102
VALIDATION_SEED = 630201
ARENA_STAGES = ((4, 630301), (8, 630302), (32, 630303))
ROOT_COUNT = 96
SOURCE_GROUP_COUNT = 32
ROOTS_PER_GROUP = 3
FIT_GROUPS = 16
DEVELOPMENT_GROUPS = 8
FINAL_GROUPS = 8
NODES_PER_MOVE = 2_000
MAX_DEPTH = 12
WORK_ORDER_PARENT_SHA = "750b0617f925cf7dd3c233330c18cd96327410a2"


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _workers(unit_count: int) -> int:
    return max(1, min(unit_count, os.cpu_count() or 1))


def _code_provenance() -> dict:
    relative_paths = (
        "scripts/f62_learned_champion_repeatability.py",
        "scripts/f59_action_spectrum_diagnosis.py",
        "scripts/f60_disjoint_policy_objective_validation.py",
        "scripts/f61_strength_first_triage.py",
        "scripts/f61_r2_fresh_strength.py",
        "generic_chess/learning/arena.py",
        "generic_chess/learning/nonlinear.py",
        "docs/architecture/GENERICCHESS_F61_MODEL_PARAMS.json",
    )
    return {
        relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in relative_paths
    }


def _load_gen1(compiled) -> tuple[LearnableMaterialCheckpoint, dict]:
    data = json.loads(MODEL_PARAMS.read_text(encoding="utf-8"))
    row = next(
        item for item in data["corrected_candidates"]
        if item["candidate_id"] == GEN1_CANDIDATE
    )
    parent = f59._parent(LABEL)
    gen1 = f61r2._candidate_checkpoint(parent, row)
    if (
        row["corrected_checkpoint_id"] != GEN1_ID
        or row["checkpoint_id"] != GEN1_ID
        or gen1.checkpoint_id != GEN1_ID
        or row["corrected_model_sha256"] != stable_sha256(row["model"])
    ):
        raise RuntimeError("F62 Gen1 durable champion identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1, row


def _fresh_records(compiled, *, smoke: bool = False):
    group_count = 3 if smoke else SOURCE_GROUP_COUNT
    roots_per_group = 1 if smoke else ROOTS_PER_GROUP
    root_count = group_count * roots_per_group
    openings = generate_arena_openings(
        compiled,
        count=group_count,
        seed=DATA_OPENING_SEED,
        min_plies=2,
        max_plies=6,
    )
    corpus = generate_diagnostic_corpus(
        compiled,
        openings,
        count=root_count,
        seed=DATA_CORPUS_SEED,
        min_plies=8,
        max_plies=40,
    )
    if smoke:
        split_by_group = {0: "fit", 1: "development", 2: "final_holdout"}
    else:
        split_by_group = {
            **{index: "fit" for index in range(FIT_GROUPS)},
            **{
                index: "development"
                for index in range(FIT_GROUPS, FIT_GROUPS + DEVELOPMENT_GROUPS)
            },
            **{
                index: "final_holdout"
                for index in range(
                    FIT_GROUPS + DEVELOPMENT_GROUPS, SOURCE_GROUP_COUNT
                )
            },
        }
    records = []
    for position in corpus.positions:
        group_index = position.index % group_count
        opening = openings.openings[group_index]
        records.append({
            **f59._record_dict(position),
            "source_group": f"F62_OPENING_{group_index:02d}_{opening.final_position_key}",
            "source_split": split_by_group[group_index],
        })
    keys = [record["position_key"] for record in records]
    if len(set(keys)) != len(keys):
        raise RuntimeError("F62 fresh corpus contains duplicate positions")
    groups_by_split = {
        split: sorted({
            record["source_group"] for record in records
            if record["source_split"] == split
        })
        for split in ("fit", "development", "final_holdout")
    }
    if any(
        set(groups_by_split[left]) & set(groups_by_split[right])
        for left in groups_by_split for right in groups_by_split if left != right
    ):
        raise RuntimeError("F62 source group crosses a split boundary")
    expected_counts = (
        {"fit": 1, "development": 1, "final_holdout": 1}
        if smoke else
        {"fit": 48, "development": 24, "final_holdout": 24}
    )
    actual_counts = Counter(record["source_split"] for record in records)
    if dict(actual_counts) != expected_counts:
        raise RuntimeError(f"F62 split sizes differ from frozen contract: {actual_counts}")
    provenance = {
        "opening_seed": DATA_OPENING_SEED,
        "corpus_seed": DATA_CORPUS_SEED,
        "opening_corpus_id": openings.corpus_id,
        "diagnostic_corpus_id": corpus.corpus_id,
        "records_sha256": stable_sha256(records),
        "root_count": len(records),
        "source_group_count": group_count,
        "roots_per_source_group": roots_per_group,
        "split_root_counts": dict(actual_counts),
        "split_source_groups": groups_by_split,
        "position_overlap_count": 0,
        "source_group_overlap_count": 0,
    }
    return records, provenance


def _stage_manifest(compiled, gen1, provenance, *, smoke: bool):
    identity = {
        "work_order": WORK_ORDER,
        "work_order_parent_repository_sha": WORK_ORDER_PARENT_SHA,
        "code_sha256": _code_provenance(),
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "data": provenance,
        "mechanism": {
            "ruleset": "Standard Shogi semantic rules",
            "teacher": "Gen1 semantic Native search",
            "state_encoding": "generic semantic_state_features",
            "objective": "PAIRWISE_RANKING",
            "width": f59.MODEL_WIDTH,
            "regularization": f59.MODEL_REGULARIZATION,
            "training_seed": TRAINING_SEED,
            "root_budgets": list((50, 100, 200) if smoke else f59.ROOT_BUDGETS),
            "equal_child_budgets": list(
                (50, 100, 200) if smoke else f59.SPECTRUM_BUDGETS
            ),
            "smoke": smoke,
        },
        "validation_seed": VALIDATION_SEED,
        "arena_stages": [list(stage) for stage in ARENA_STAGES],
    }
    return {
        "schema": "generic-chess-f62-stage-v1",
        "identity": identity,
        "identity_sha256": stable_sha256(identity),
    }


def _ensure_exact(path: Path, expected: dict, description: str) -> None:
    if path.is_file():
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{description} is corrupt") from exc
        if actual != expected:
            raise RuntimeError(f"{description} identity mismatch")
    else:
        _atomic_json(path, expected)


def _spectrum_identity(stage_sha: str, index: int, record: dict) -> dict:
    return {
        "stage_identity_sha256": stage_sha,
        "root_index": index,
        "record": record,
    }


def _load_spectrum_unit(path: Path, identity: dict):
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"F62 spectrum unit is corrupt: {path.name}") from exc
    digest = stable_sha256(identity)
    if (
        payload.get("schema") != "generic-chess-f62-spectrum-v1"
        or payload.get("identity") != identity
        or payload.get("identity_sha256") != digest
    ):
        raise RuntimeError(f"F62 spectrum unit identity mismatch: {path.name}")
    metadata = payload.get("root_metadata")
    if not isinstance(metadata, dict) or not metadata.get("action_rows"):
        raise RuntimeError(f"F62 spectrum unit is incomplete: {path.name}")
    rows = f60._rows_from_meta(metadata)
    return rows, metadata


def _compute_spectra(compiled, native, gen1, records, stage_sha, *, smoke: bool):
    directory = PROGRESS / ("spectrum-smoke" if smoke else "spectrum")
    directory.mkdir(parents=True, exist_ok=True)
    complete = {}
    missing = []
    identities = {}
    for index, record in enumerate(records):
        identity = _spectrum_identity(stage_sha, index, record)
        identities[index] = identity
        loaded = _load_spectrum_unit(directory / f"root-{index:03d}.json", identity)
        if loaded is None:
            missing.append(index)
        else:
            complete[index] = loaded

    def execute(index):
        rows, metadata = f59._spectrum_for_root(
            compiled, native, gen1, gen1, records[index], smoke=smoke
        )
        return index, rows, metadata

    prior_worker_flag = os.environ.get("F59_ROOT_WORKER")
    os.environ["F59_ROOT_WORKER"] = "1"
    try:
        with ThreadPoolExecutor(max_workers=_workers(len(missing))) as pool:
            futures = {pool.submit(execute, index): index for index in missing}
            for future in as_completed(futures):
                index, rows, metadata = future.result()
                identity = identities[index]
                _atomic_json(directory / f"root-{index:03d}.json", {
                    "schema": "generic-chess-f62-spectrum-v1",
                    "identity": identity,
                    "identity_sha256": stable_sha256(identity),
                    "root_metadata": metadata,
                })
                complete[index] = (rows, metadata)
                print(
                    f"F62_SPECTRUM_COMPLETE={len(complete)}/{len(records)} "
                    f"root={index}",
                    flush=True,
                )
    finally:
        if prior_worker_flag is None:
            os.environ.pop("F59_ROOT_WORKER", None)
        else:
            os.environ["F59_ROOT_WORKER"] = prior_worker_flag
    return [complete[index] for index in range(len(records))]


def _hand_type_indices(compiled):
    current = tuple(sorted(compiled.support.type_metadata))
    base = tuple(sorted(
        piece_type.type_id for piece_type in compiled._legacy_compiled.piece_types
    ))
    return tuple(current.index(type_id) for type_id in base)


def _freeze_gen2(compiled, gen1, summary, provenance, *, smoke: bool):
    fit = summary["split_indices"]["fit"]
    development = summary["split_indices"]["development"]
    final = summary["split_indices"]["final_holdout"]
    if not fit or not development or not final:
        raise RuntimeError("F62 stable ordinary roots are insufficient in a frozen split")
    roots, features, base, targets, groups = f60._train_rows(summary, fit)
    model = f61._fit_serializable(
        features, base, targets, groups, "PAIRWISE_RANKING", TRAINING_SEED
    )
    model_payload = replace(
        model,
        hand_type_indices=_hand_type_indices(compiled),
        perspective="successor_root_q",
    ).to_dict()
    training_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "records_sha256": provenance["records_sha256"],
        "fit_source_groups": provenance["split_source_groups"]["fit"],
        "fit_position_keys": [
            summary["roots_metadata"][index]["position_key"] for index in fit
        ],
        "fit_action_count": len(features),
        "objective": "PAIRWISE_RANKING",
        "width": f59.MODEL_WIDTH,
        "regularization": f59.MODEL_REGULARIZATION,
        "seed": TRAINING_SEED,
        "perspective": "successor_root_q",
        "smoke": smoke,
    }
    gen2 = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=model_payload,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256(training_identity),
        training_seed=TRAINING_SEED,
    )
    artifact_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "gen2_checkpoint_id": gen2.checkpoint_id,
        "model_sha256": stable_sha256(model_payload),
        "training": training_identity,
    }
    artifact_path = OUT / "gen2_checkpoint_smoke.json" if smoke else GEN2_PATH
    if artifact_path.is_file():
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        if payload.get("identity") != artifact_identity:
            raise RuntimeError("persisted F62 Gen2 identity mismatch")
        persisted = LearnableMaterialCheckpoint.from_dict(payload["checkpoint"])
        if persisted.checkpoint_id != gen2.checkpoint_id:
            raise RuntimeError("persisted F62 Gen2 checkpoint does not reconstruct")
        gen2 = persisted
    else:
        _atomic_json(artifact_path, {
            "schema": "generic-chess-f62-gen2-v1",
            "identity": artifact_identity,
            "identity_sha256": stable_sha256(artifact_identity),
            "checkpoint": gen2.to_dict(),
        })

    def diagnostic(indices):
        root_rows = [summary["roots"][index] for index in indices]
        predictions = [f59._predict_total_q(root, model.predict) for root in root_rows]
        return f60._metrics_with_normalized_regret(root_rows, predictions)

    return gen2, artifact_identity, {
        "fit_root_count": len(fit),
        "fit_action_count": len(features),
        "development_source_groups": provenance["split_source_groups"]["development"],
        "final_source_groups": provenance["split_source_groups"]["final_holdout"],
        "development_metrics_diagnostic_only": diagnostic(development),
        "final_metrics_diagnostic_only": diagnostic(final),
    }


def _search_payload(result):
    elapsed = float(result.elapsed_seconds)
    return {
        "action": None if result.action is None else f59.action_to_dict(result.action),
        "score": int(result.score),
        "nodes": int(result.nodes),
        "elapsed_seconds": elapsed,
        "nps": float(result.nodes) / elapsed if elapsed > 0.0 else None,
        "completed_depth": int(result.completed_depth),
        "selective_depth": int(result.selective_depth),
        "termination_reason": str(result.termination_reason),
        "used_fallback": bool(result.used_fallback),
    }


def _validate_decisions(compiled, native, gen1, gen2, stage_sha, *, smoke):
    count = 2 if smoke else 8
    nodes = 100 if smoke else NODES_PER_MOVE
    depth = 4 if smoke else MAX_DEPTH
    openings = generate_arena_openings(
        compiled, count=count, seed=VALIDATION_SEED, min_plies=2, max_plies=6
    )
    directory = PROGRESS / ("validation-smoke" if smoke else "validation")
    directory.mkdir(parents=True, exist_ok=True)

    def identity(index):
        opening = openings.openings[index]
        return {
            "stage_identity_sha256": stage_sha,
            "gen1_checkpoint_id": gen1.checkpoint_id,
            "gen2_checkpoint_id": gen2.checkpoint_id,
            "opening": openings.to_dict()["openings"][index],
            "nodes": nodes,
            "max_depth": depth,
        }

    def load(index):
        path = directory / f"opening-{index:02d}.json"
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = identity(index)
        if (
            payload.get("schema") != "generic-chess-f62-validation-v1"
            or payload.get("identity") != expected
            or payload.get("identity_sha256") != stable_sha256(expected)
        ):
            raise RuntimeError(f"F62 validation identity mismatch: {path.name}")
        return payload["row"]

    def execute(index):
        opening = openings.openings[index]
        record = {"action_history": [f59.action_to_dict(a) for a in opening.actions]}
        session = f59._session(compiled, record)
        limits = SearchLimits(
            max_depth=depth, max_nodes=nodes, quiescence_max_depth=0
        )
        parent_result = SemanticSearchEngine(
            compiled, native, checkpoint=gen1, tt_megabytes=8
        ).search(session, limits)
        child_result = SemanticSearchEngine(
            compiled, native, checkpoint=gen2, tt_megabytes=8
        ).search(session, limits)
        parent_payload = _search_payload(parent_result)
        child_payload = _search_payload(child_result)
        return index, {
            "opening_id": opening.final_position_key,
            "gen1": parent_payload,
            "gen2": child_payload,
            "decision_changed": parent_payload["action"] != child_payload["action"],
        }

    rows = {}
    missing = []
    for index in range(count):
        row = load(index)
        if row is None:
            missing.append(index)
        else:
            rows[index] = row
    with ThreadPoolExecutor(max_workers=_workers(len(missing))) as pool:
        futures = {pool.submit(execute, index): index for index in missing}
        for future in as_completed(futures):
            index, row = future.result()
            unit_identity = identity(index)
            _atomic_json(directory / f"opening-{index:02d}.json", {
                "schema": "generic-chess-f62-validation-v1",
                "identity": unit_identity,
                "identity_sha256": stable_sha256(unit_identity),
                "row": row,
            })
            rows[index] = row
    ordered = [rows[index] for index in range(count)]
    changed = [row for row in ordered if row["decision_changed"]]
    return {
        "opening_count": count,
        "decision_changes": len(changed),
        "first_meaningful_divergences": changed[:3],
        "rows": ordered,
    }


def _role_score(games):
    wins = sum(game.winner == game.child_owner for game in games)
    draws = sum(game.winner is None for game in games)
    losses = len(games) - wins - draws
    return {
        "games": len(games),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "score_rate": (wins + 0.5 * draws) / len(games) if games else 0.0,
    }


def _telemetry_summary(summary):
    games = [
        game for pair in summary.pairs
        for game in (pair.game_child_owner0, pair.game_child_owner1)
    ]
    searches = [metric for game in games for metric in game.search_metrics]
    by_role = {}
    for role in ("parent", "child"):
        rows = [row for row in searches if row["engine_role"] == role]
        nodes = sum(row["nodes"] for row in rows)
        elapsed = sum(row["elapsed_seconds"] for row in rows)
        depths = [row["completed_depth"] for row in rows]
        by_role[role] = {
            "decisions": len(rows),
            "nodes": nodes,
            "elapsed_seconds": elapsed,
            "aggregate_nps": nodes / elapsed if elapsed > 0.0 else None,
            "completed_depth_median": statistics.median(depths) if depths else None,
            "completed_depth_min": min(depths) if depths else None,
            "completed_depth_max": max(depths) if depths else None,
        }
    return {
        "owner_role_split": {
            "child_owner0": _role_score([g for g in games if g.child_owner == 0]),
            "child_owner1": _role_score([g for g in games if g.child_owner == 1]),
        },
        "termination_modes": dict(sorted(Counter(
            row["termination_reason"] for row in searches
        ).items())),
        "search_by_engine_role": by_role,
    }


def _arena_payload(summary):
    payload = f61._arena_payload(summary)
    payload.update(_telemetry_summary(summary))
    return payload


def _run_arena_stage(compiled, native, gen1, gen2, pairs, seed, *, smoke):
    actual_pairs = min(pairs, {4: 1, 8: 2, 32: 3}[pairs]) if smoke else pairs
    nodes = 100 if smoke else NODES_PER_MOVE
    depth = 4 if smoke else MAX_DEPTH
    openings = generate_arena_openings(
        compiled, count=actual_pairs, seed=seed, min_plies=2, max_plies=6
    )
    summary = run_arena_resumable(
        compiled,
        native,
        gen1,
        gen2,
        ArenaConfig(
            pairs=actual_pairs,
            nodes_per_move=nodes,
            max_depth=depth,
            tt_megabytes=2 if smoke else 8,
            opening_seed=seed,
            opening_count=actual_pairs,
            min_plies=2,
            max_plies=6,
            workers=_workers(actual_pairs),
        ),
        progress_dir=PROGRESS / (
            f"arena-smoke-{pairs}-seed-{seed}"
            if smoke else f"arena-{pairs}-seed-{seed}"
        ),
        openings=openings,
        capture_search_metrics=True,
    )
    return _arena_payload(summary)


def run(*, smoke: bool = False):
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1, gen1_row = _load_gen1(compiled)
    records, provenance = _fresh_records(compiled, smoke=smoke)
    manifest = _stage_manifest(compiled, gen1, provenance, smoke=smoke)
    manifest_path = (
        PROGRESS / "stage-manifest-smoke.json" if smoke else STAGE_MANIFEST_PATH
    )
    _ensure_exact(manifest_path, manifest, "F62 stage manifest")
    spectra = _compute_spectra(
        compiled, native, gen1, records, manifest["identity_sha256"], smoke=smoke
    )
    summary = f60._summarize_spectrum(
        records, spectra, (1, 2, 3) if smoke else f60.SPLIT_ENDS
    )
    gen2, gen2_identity, training = _freeze_gen2(
        compiled, gen1, summary, provenance, smoke=smoke
    )
    validation = _validate_decisions(
        compiled, native, gen1, gen2, manifest["identity_sha256"], smoke=smoke
    )
    result = {
        "work_order": WORK_ORDER,
        "classification": "PENDING_ARENA",
        "teacher_metrics_are_diagnostic_only": True,
        "strength_authority": "equal-budget fresh parent-child Arena",
        "gen1": {
            "candidate_id": GEN1_CANDIDATE,
            "checkpoint_id": gen1.checkpoint_id,
            "model_sha256": gen1_row["corrected_model_sha256"],
        },
        "gen2": gen2_identity,
        "fresh_data": provenance,
        "stage_identity_sha256": manifest["identity_sha256"],
        "training": training,
        "search_validation": validation,
        "arena": {},
    }
    if validation["decision_changes"] == 0:
        result["classification"] = "NO_EFFECTIVE_LEARNING"
        _atomic_json(RESULT_PATH if not smoke else OUT / "f62_smoke_results.json", result)
        return result

    four = _run_arena_stage(
        compiled, native, gen1, gen2, *ARENA_STAGES[0], smoke=smoke
    )
    result["arena"]["4_pairs"] = four
    catastrophic = (
        four["mean_pair_score"] <= 0.25
        and four["child_worse_pairs"] >= four["pair_count"] - 1
    )
    if catastrophic:
        result["classification"] = "GEN2_EARLY_STOP_CATASTROPHIC"
        _atomic_json(RESULT_PATH if not smoke else OUT / "f62_smoke_results.json", result)
        return result
    _atomic_json(PARTIAL_PATH, result)

    eight = _run_arena_stage(
        compiled, native, gen1, gen2, *ARENA_STAGES[1], smoke=smoke
    )
    result["arena"]["8_pairs"] = eight
    if eight["mean_pair_score"] < 0.5:
        result["classification"] = "GEN2_NOT_POSITIVELY_COMPETITIVE"
        _atomic_json(RESULT_PATH if not smoke else OUT / "f62_smoke_results.json", result)
        return result
    _atomic_json(PARTIAL_PATH, result)

    confirmation = _run_arena_stage(
        compiled, native, gen1, gen2, *ARENA_STAGES[2], smoke=smoke
    )
    result["arena"]["32_pairs"] = confirmation
    result["classification"] = (
        "REPEATABLE_AUTONOMOUS_STRENGTH_IMPROVEMENT_SIGNAL"
        if confirmation["bootstrap_low"] > 0.5
        else "GEN2_REPEATABILITY_NOT_CONFIRMED"
    )
    _atomic_json(RESULT_PATH if not smoke else OUT / "f62_smoke_results.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = run(smoke=args.smoke)
    print(json.dumps({
        "classification": result["classification"],
        "gen1_checkpoint_id": result["gen1"]["checkpoint_id"],
        "gen2_checkpoint_id": result["gen2"]["gen2_checkpoint_id"],
        "decision_changes": result["search_validation"]["decision_changes"],
        "arena_scores": {
            stage: payload["mean_pair_score"]
            for stage, payload in result["arena"].items()
        },
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
