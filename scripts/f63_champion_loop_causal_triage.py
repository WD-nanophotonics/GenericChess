"""F63 causal triage for the champion-retention learning loop.

The first gate tests whether the accepted Gen1 search teacher is itself a
policy-improvement operator.  Only a positive teacher result unlocks the
predeclared same-data, multi-seed candidate loop.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import (
    ArenaConfig,
    ArenaDecisionCriterion,
    ArenaExecutionCaps,
    arena_decision_bound,
    run_arena_game_resumable,
    run_arena_resumable,
    _pair_from_dict,
    _validate_game_telemetry,
    _validate_replayed_game,
)
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f60_disjoint_policy_objective_validation as f60
from scripts import f61_r2_fresh_strength as f61r2
from scripts import f61_strength_first_triage as f61
from scripts import f62_learned_champion_repeatability as f62


WORK_ORDER = "GENERICCHESS-F63-CHAMPION-LOOP-CAUSAL-TRIAGE"
LABEL = f62.LABEL
OUT = ROOT / ".generic_chess_flow" / "f63-champion-loop-causal-triage"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f63_results.json"
CANDIDATE_PATH = OUT / "candidates.json"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
GEN1_ID = f62.GEN1_ID
GEN1_CANDIDATE = f62.GEN1_CANDIDATE
GEN2_SEEDS = (59011, 59012, 59013)
SHALLOW_NODES = 2_000
DEEP_NODES = 20_000
MAX_DEPTH = 12
TEACHER_STAGES = ((4, 630401), (8, 630402))
COMMON_TRIAGE_SEED = 630403
SELECTED_FRESH_SEEDS = (8, 630404), (32, 630405)
PARENT_SHA = "a19a8048b36b6460db7ec6aeefa2bf3e3172d5e6"
RESUME_PARENT_SHA = "acc74ac9063530da7137b460d2bc035858d30809"
TEACHER_DECISION_PATH = ROOT / "docs" / "architecture" / "GENERICCHESS_F63_TEACHER_DECISION_V1.json"
TEACHER_PROGRESS = PROGRESS / "teacher-8-seed-630402"
RESUME_WORK_ORDER = "GENERICCHESS-F63-R1-R3-CANDIDATE-RESUME-HARNESS-AND-COMPUTE-PLAN"
RESUME_LOGICAL_CPUS = 10
RESUME_PER_GAME_WALL_SECONDS = 900.0
RESUME_PER_GAME_NODES = 200_000
RESUME_PER_GAME_PLIES = 80
RESUME_STAGE_WALL_SECONDS = {4: 3_600.0, 8: 7_200.0, 32: 28_800.0}


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _workers(count: int) -> int:
    return max(1, min(count, os.cpu_count() or 1))


def _load_gen1(compiled):
    data = json.loads(f62.MODEL_PARAMS.read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"]
               if item["candidate_id"] == GEN1_CANDIDATE)
    parent = f59._parent(LABEL)
    gen1 = f61r2._candidate_checkpoint(parent, row)
    if gen1.checkpoint_id != GEN1_ID or row["corrected_checkpoint_id"] != GEN1_ID:
        raise RuntimeError("F63 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _load_gen2():
    payload = json.loads((F62_OUT / "gen2_checkpoint.json").read_text(encoding="utf-8"))
    identity = payload["identity"]
    if identity["parent_checkpoint_id"] != GEN1_ID:
        raise RuntimeError("F62 Gen2 parent identity mismatch")
    return LearnableMaterialCheckpoint.from_dict(payload["checkpoint"]), identity


def _arena_payload(summary: object) -> dict:
    payload = f62._arena_payload(summary)
    return payload


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_teacher_decision(
    compiled,
    *,
    artifact_path: Path = TEACHER_DECISION_PATH,
    progress_dir: Path = TEACHER_PROGRESS,
) -> dict:
    """Validate the preserved seven-pair teacher evidence without rerunning it."""
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        progress_manifest_path = progress_dir / "manifest.json"
        manifest_bytes = progress_manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("F63 frozen teacher decision evidence is unavailable") from exc
    if artifact.get("schema") != "generic-chess-f63-teacher-decision-v1":
        raise RuntimeError("F63 frozen teacher decision schema mismatch")
    stage = artifact.get("stage", {})
    if (
        stage.get("requested_pairs") != 8
        or stage.get("completed_pairs") != 7
        or stage.get("opening_seed") != 630402
    ):
        raise RuntimeError("F63 frozen teacher stage identity mismatch")
    if manifest.get("schema") != "generic-chess-arena-progress-v1":
        raise RuntimeError("F63 teacher progress is not the legacy pair-v1 schema")
    identity = manifest.get("identity")
    identity_sha = manifest.get("identity_sha256")
    if not isinstance(identity, dict) or stable_sha256(identity) != identity_sha:
        raise RuntimeError("F63 teacher manifest identity is invalid")
    config = identity.get("config", {})
    if (
        identity.get("parent_checkpoint_id") != GEN1_ID
        or identity.get("child_checkpoint_id") != GEN1_ID
        or config.get("pairs") != 8
        or config.get("opening_seed") != 630402
        or config.get("opening_count") != 8
        or config.get("nodes_per_move") != SHALLOW_NODES
        or config.get("child_nodes_per_move") != DEEP_NODES
    ):
        raise RuntimeError("F63 teacher configuration identity is invalid")
    if _file_sha256(progress_manifest_path) != stage.get("manifest_sha256"):
        raise RuntimeError("F63 teacher manifest hash mismatch")
    if identity_sha != artifact.get("original_teacher_identity_sha256"):
        raise RuntimeError("F63 teacher identity hash mismatch")

    openings = generate_arena_openings(
        compiled,
        count=config["opening_count"],
        seed=config["opening_seed"],
        min_plies=config["min_plies"],
        max_plies=config["max_plies"],
    )
    if openings.to_dict()["openings"] != identity.get("ordered_openings"):
        raise RuntimeError("F63 teacher opening corpus does not replay identically")
    rows = artifact.get("pair_files")
    if not isinstance(rows, list) or [row.get("pair_index") for row in rows] != list(range(1, 8)):
        raise RuntimeError("F63 teacher pair inventory is not exactly seven pairs")
    actual_pair_names = sorted(path.name for path in progress_dir.glob("pair-*.json"))
    if actual_pair_names != sorted(row["file"] for row in rows):
        raise RuntimeError("F63 teacher pair inventory has unexpected files")
    pairs = []
    for row in rows:
        pair_path = progress_dir / row["file"]
        if _file_sha256(pair_path) != row["sha256"]:
            raise RuntimeError(f"F63 teacher pair hash mismatch: {row['file']}")
        try:
            payload = json.loads(pair_path.read_text(encoding="utf-8"))
            pair = _pair_from_dict(payload, identity_sha256=identity_sha)
            opening = openings.openings[row["pair_index"]]
            _validate_replayed_game(compiled, opening, pair.game_child_owner0)
            _validate_replayed_game(compiled, opening, pair.game_child_owner1)
            teacher_config = ArenaConfig(**config)
            _validate_game_telemetry(
                pair.game_child_owner0, teacher_config,
                capture_search_metrics=True,
            )
            _validate_game_telemetry(
                pair.game_child_owner1, teacher_config,
                capture_search_metrics=True,
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"F63 teacher pair validation failed: {row['file']}") from exc
        if pair.pair_index != row["pair_index"] or pair.opening_id != opening.final_position_key:
            raise RuntimeError(f"F63 teacher pair identity mismatch: {row['file']}")
        if pair.child_pair_score != row["pair_score"]:
            raise RuntimeError(f"F63 teacher pair score mismatch: {row['file']}")
        pairs.append(pair)
    scores = [pair.child_pair_score for pair in pairs]
    bound = arena_decision_bound(scores, 8, criterion=artifact["criterion"])
    expected = {
        "observed_total": sum(scores),
        "observed_mean": sum(scores) / len(scores),
        "observed_better_pairs": sum(score > 0.5 for score in scores),
        "observed_tied_pairs": sum(score == 0.5 for score in scores),
        "observed_worse_pairs": sum(score < 0.5 for score in scores),
    }
    for key, value in expected.items():
        if isinstance(value, float):
            matches = abs(float(artifact.get(key)) - value) <= 1e-12
        else:
            matches = artifact.get(key) == value
        if not matches:
            raise RuntimeError(f"F63 teacher decision field mismatch: {key}")
    if (
        bound.decision_state != artifact.get("decision_state")
        or abs(bound.worst_final_mean - artifact.get("worst_possible_final_mean")) > 1e-12
        or bound.worst_better_pairs != artifact.get("worst_possible_final_better_pairs")
        or bound.worst_tied_pairs != artifact.get("worst_possible_final_tied_pairs")
        or bound.worst_worse_pairs != artifact.get("worst_possible_final_worse_pairs")
        or bound.strength_estimate_complete != artifact.get("strength_estimate_complete")
    ):
        raise RuntimeError("F63 frozen teacher decision bound mismatch")
    return {"artifact": artifact, "manifest": manifest, "pairs": pairs, "bound": bound}


def _run_teacher_stage(compiled, native, gen1, pairs: int, seed: int, *, smoke: bool):
    actual_pairs = min(pairs, 1) if smoke else pairs
    shallow = 100 if smoke else SHALLOW_NODES
    deep = 200 if smoke else DEEP_NODES
    openings = generate_arena_openings(
        compiled, count=actual_pairs, seed=seed, min_plies=2, max_plies=6
    )
    config = ArenaConfig(
        pairs=actual_pairs,
        nodes_per_move=shallow,
        parent_nodes_per_move=shallow,
        child_nodes_per_move=deep,
        max_depth=4 if smoke else MAX_DEPTH,
        tt_megabytes=2 if smoke else 8,
        opening_seed=seed,
        opening_count=actual_pairs,
        min_plies=2,
        max_plies=6,
        workers=_workers(actual_pairs),
    )
    summary = run_arena_resumable(
        compiled, native, gen1, gen1, config,
        progress_dir=PROGRESS / (
            f"teacher-smoke-{pairs}-seed-{seed}"
            if smoke else f"teacher-{pairs}-seed-{seed}"
        ),
        openings=openings,
        capture_search_metrics=True,
    )
    payload = _arena_payload(summary)
    payload.update({
        "deep_nodes_per_move": deep,
        "shallow_nodes_per_move": shallow,
        "teacher": "Gen1 deep versus Gen1 shallow",
    })
    return payload


def _teacher_is_clearly_supported(payload: dict) -> bool:
    return (
        payload["mean_pair_score"] >= 0.75
        and payload["child_better_pairs"] > payload["child_worse_pairs"]
    )


def _load_f62_training_summary(compiled, gen1):
    records, provenance = f62._fresh_records(compiled, smoke=False)
    if provenance["records_sha256"] != F62_RECORDS_SHA:
        raise RuntimeError("F62 fresh corpus identity mismatch")
    manifest = json.loads((F62_OUT / "progress" / "stage-manifest.json").read_text())
    if manifest["identity_sha256"] != F62_STAGE_SHA:
        raise RuntimeError("F62 stage identity mismatch")
    computed = []
    for index, record in enumerate(records):
        identity = f62._spectrum_identity(F62_STAGE_SHA, index, record)
        loaded = f62._load_spectrum_unit(
            F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json",
            identity,
        )
        if loaded is None:
            raise RuntimeError(f"missing F62 action spectrum root {index}")
        computed.append(loaded)
    summary = f60._summarize_spectrum(records, computed, f60.SPLIT_ENDS)
    if not summary["split_indices"]["fit"]:
        raise RuntimeError("F62 fit split is empty")
    gen2, gen2_identity = _load_gen2()
    if gen2_identity["training"]["records_sha256"] != F62_RECORDS_SHA:
        raise RuntimeError("F62 Gen2 training identity mismatch")
    gen2.validate_ruleset(compiled)
    return summary, provenance, gen2, gen2_identity


def _fit_candidate(compiled, gen1, summary, provenance, seed: int):
    fit = summary["split_indices"]["fit"]
    _roots, features, base, targets, groups = f60._train_rows(summary, fit)
    model = f61._fit_serializable(
        features, base, targets, groups, "PAIRWISE_RANKING", seed
    )
    model_payload = replace(
        model,
        hand_type_indices=f62._hand_type_indices(compiled),
        perspective="successor_root_q",
    ).to_dict()
    training_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "records_sha256": provenance["records_sha256"],
        "fit_source_groups": provenance["split_source_groups"]["fit"],
        "fit_action_count": len(features),
        "objective": "PAIRWISE_RANKING",
        "width": f59.MODEL_WIDTH,
        "regularization": f59.MODEL_REGULARIZATION,
        "seed": seed,
        "perspective": "successor_root_q",
        "source_stage_identity_sha256": F62_STAGE_SHA,
    }
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=model_payload,
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256(training_identity),
        training_seed=seed,
    )
    return candidate, {
        "seed": seed,
        "checkpoint_id": candidate.checkpoint_id,
        "model_sha256": stable_sha256(model_payload),
        "parent_checkpoint_id": gen1.checkpoint_id,
        "training": training_identity,
        "checkpoint": candidate.to_dict(),
    }


def _candidate_caps(pairs: int) -> ArenaExecutionCaps:
    if pairs not in RESUME_STAGE_WALL_SECONDS:
        raise ValueError(f"unsupported F63 candidate stage size: {pairs}")
    return ArenaExecutionCaps(
        per_game_wall_seconds=RESUME_PER_GAME_WALL_SECONDS,
        per_game_nodes=RESUME_PER_GAME_NODES,
        per_game_plies=RESUME_PER_GAME_PLIES,
        max_stage_games=2 * pairs,
        max_concurrent_games=min(RESUME_LOGICAL_CPUS, 2 * pairs, 16),
        stage_wall_seconds=RESUME_STAGE_WALL_SECONDS[pairs],
        logical_cpu_count=RESUME_LOGICAL_CPUS,
    )


def _run_candidate_stage(
    compiled,
    native,
    gen1,
    candidate,
    pairs,
    seed,
    label,
    *,
    stop_on_decision: bool = False,
    decision_criterion=None,
):
    openings = generate_arena_openings(
        compiled, count=pairs, seed=seed, min_plies=2, max_plies=6
    )
    run_result = run_arena_game_resumable(
        compiled, native, gen1, candidate,
        ArenaConfig(
            pairs=pairs,
            nodes_per_move=SHALLOW_NODES,
            max_depth=MAX_DEPTH,
            tt_megabytes=8,
            opening_seed=seed,
            opening_count=pairs,
            min_plies=2,
            max_plies=6,
            workers=_workers(pairs),
        ),
        progress_dir=PROGRESS / f"{label}-seed-{seed}",
        openings=openings,
        capture_search_metrics=True,
        execution_caps=_candidate_caps(pairs),
        stage_id=label,
        pause_file=OUT / "candidate-pause.request",
        decision_criterion=decision_criterion,
        stop_on_decision=stop_on_decision,
    )
    payload = {
        "status": run_result.status,
        "completed_games": run_result.completed_games,
        "completed_pairs": run_result.completed_pairs,
        "total_games": run_result.total_games,
        "stop_reason": run_result.reason,
        "decision_state": run_result.decision_bound.decision_state,
        "decision_sufficient": run_result.decision_bound.decision_sufficient,
        "strength_estimate_complete": run_result.decision_bound.strength_estimate_complete,
    }
    if run_result.summary is not None:
        payload.update(_arena_payload(run_result.summary))
    return payload


def _selected_eight_continuation(stage: dict) -> str:
    """Choose 32-pair continuation from decision state and execution state."""
    state = stage.get("decision_state")
    if state == "PASS_LOCKED":
        return "RUN_32"
    if state == "FAIL_LOCKED":
        return "FAIL_LOCKED"
    if stage.get("status") != "COMPLETE":
        return "INCONCLUSIVE_RESUMABLE"
    return "RUN_32"


def _select_candidate(results):
    # Every key is a game-result statistic; seed is only the deterministic tie break.
    return min(
        results,
        key=lambda row: (
            -row["arena"]["mean_pair_score"],
            -row["arena"]["game_wins"],
            row["arena"]["game_losses"],
            row["seed"],
        ),
    )


def _run_candidate_resume_legacy(*, smoke: bool = False):
    """Resume F63 after the frozen teacher decision; never runs teacher games."""
    if smoke:
        raise RuntimeError(
            "F63 candidate resume has no reduced smoke mode; use the bounded protocol tests"
        )
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    teacher = validate_frozen_teacher_decision(compiled)
    teacher_artifact = teacher["artifact"]
    if (
        not teacher_artifact.get("authorizes_candidate_branch")
        or teacher["bound"].decision_state != "PASS_LOCKED"
    ):
        raise RuntimeError("F63 frozen teacher decision does not unlock candidates")

    summary, provenance, persisted_gen2, persisted_identity = (
        _load_f62_training_summary(compiled, gen1)
    )
    candidates = []
    for seed in GEN2_SEEDS:
        if seed == 59012:
            candidate = persisted_gen2
            if candidate.checkpoint_id != persisted_identity["gen2_checkpoint_id"]:
                raise RuntimeError("F62 persisted Gen2 checkpoint identity mismatch")
            identity = persisted_identity | {
                "checkpoint_id": persisted_identity["gen2_checkpoint_id"],
                "reused_exact_f62_candidate": True,
            }
        else:
            candidate, identity = _fit_candidate(
                compiled, gen1, summary, provenance, seed
            )
        candidates.append({"seed": seed, "checkpoint": candidate, "identity": identity})

    # This durable identity freeze is deliberately before the first candidate
    # Arena call.  A crash after this write cannot create an unregistered
    # candidate game.
    _atomic_json(CANDIDATE_PATH, {
        "schema": "generic-chess-f63-candidates-v1",
        "source_stage_identity_sha256": F62_STAGE_SHA,
        "records_sha256": F62_RECORDS_SHA,
        "teacher_decision_identity_sha256": teacher_artifact[
            "original_teacher_identity_sha256"
        ],
        "candidates": [row["identity"] for row in candidates],
    })

    result = {
        "work_order": RESUME_WORK_ORDER,
        "parent_repository_sha": RESUME_PARENT_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "teacher": {
            "status": "FROZEN_DECISION_ONLY",
            "artifact": str(TEACHER_DECISION_PATH.relative_to(ROOT)).replace("\\", "/"),
            "decision_state": teacher["bound"].decision_state,
            "decision_sufficient": teacher["bound"].decision_sufficient,
            "strength_estimate_complete": teacher["bound"].strength_estimate_complete,
        },
        "candidate_loop": {"status": "IDENTITIES_FROZEN"},
    }

    common = []
    for row in candidates:
        arena = _run_candidate_stage(
            compiled, native, gen1, row["checkpoint"], 4,
            COMMON_TRIAGE_SEED, f"candidate-{row['seed']}-common-4",
        )
        if arena["status"] != "COMPLETE":
            result["candidate_loop"] = {
                "status": "INCOMPLETE",
                "candidates": common,
                "incomplete_stage": row["seed"],
                "arena": arena,
            }
            _atomic_json(RESULT_PATH, result)
            return result
        common.append({
            "seed": row["seed"],
            "checkpoint_id": row["identity"]["checkpoint_id"],
            "arena": arena,
        })

    selected = _select_candidate(common)
    result["candidate_loop"] = {
        "status": "COMMON_COMPLETE",
        "source_stage_identity_sha256": F62_STAGE_SHA,
        "records_sha256": F62_RECORDS_SHA,
        "candidates": common,
        "selected_seed": selected["seed"],
        "selected_checkpoint_id": selected["checkpoint_id"],
    }
    selected_candidate = next(
        row["checkpoint"] for row in candidates if row["seed"] == selected["seed"]
    )
    selected_eight = _run_candidate_stage(
        compiled, native, gen1, selected_candidate, 8, 630404,
        f"selected-{selected['seed']}-8",
        stop_on_decision=True,
        decision_criterion="f63_teacher_gate",
    )
    result["candidate_loop"]["selected_8_pairs"] = selected_eight
    continuation = _selected_eight_continuation(selected_eight)
    result["candidate_loop"]["selected_8_continuation"] = continuation
    if continuation == "FAIL_LOCKED":
        result["candidate_loop"]["classification"] = (
            "TEACHER_IMPROVES_BUT_REPLACEMENT_DISTILLATION_FAILS"
        )
        _atomic_json(RESULT_PATH, result)
        return result
    if continuation == "INCONCLUSIVE_RESUMABLE":
        result["candidate_loop"]["classification"] = (
            "CANDIDATE_STAGE_INCOMPLETE_RESUMABLE"
        )
        _atomic_json(RESULT_PATH, result)
        return result

    selected_32 = _run_candidate_stage(
        compiled, native, gen1, selected_candidate, 32, 630405,
        f"selected-{selected['seed']}-32",
        decision_criterion="f63_teacher_gate",
    )
    result["candidate_loop"]["selected_32_pairs"] = selected_32
    if selected_32["status"] != "COMPLETE":
        result["candidate_loop"]["classification"] = (
            "CANDIDATE_CONFIRMATION_INCOMPLETE_RESUMABLE"
        )
        _atomic_json(RESULT_PATH, result)
        return result
    result["candidate_loop"]["classification"] = (
        "BOUNDED_CHAMPION_LOOP_REPEATABILITY_SIGNAL"
        if result["candidate_loop"].get("selected_32_pairs", {}).get(
            "bootstrap_low", 0.0
        ) > 0.5
        else "TEACHER_IMPROVES_BUT_REPLACEMENT_DISTILLATION_FAILS"
    )
    _atomic_json(RESULT_PATH, result)
    return result


def _resume_context(compiled):
    gen1 = _load_gen1(compiled)
    teacher = validate_frozen_teacher_decision(compiled)
    teacher_artifact = teacher["artifact"]
    if (
        not teacher_artifact.get("authorizes_candidate_branch")
        or teacher["bound"].decision_state != "PASS_LOCKED"
    ):
        raise RuntimeError("F63 frozen teacher decision does not unlock candidates")
    summary, provenance, persisted_gen2, persisted_identity = (
        _load_f62_training_summary(compiled, gen1)
    )
    candidates = []
    for seed in GEN2_SEEDS:
        if seed == 59012:
            candidate = persisted_gen2
            if candidate.checkpoint_id != persisted_identity["gen2_checkpoint_id"]:
                raise RuntimeError("F62 persisted Gen2 checkpoint identity mismatch")
            identity = persisted_identity | {
                "checkpoint_id": persisted_identity["gen2_checkpoint_id"],
                "reused_exact_f62_candidate": True,
            }
        else:
            candidate, identity = _fit_candidate(
                compiled, gen1, summary, provenance, seed
            )
        candidates.append({"seed": seed, "checkpoint": candidate, "identity": identity})
    candidate_payload = {
        "schema": "generic-chess-f63-candidates-v1",
        "source_stage_identity_sha256": F62_STAGE_SHA,
        "records_sha256": F62_RECORDS_SHA,
        "teacher_decision_identity_sha256": teacher_artifact[
            "original_teacher_identity_sha256"
        ],
        "candidates": [row["identity"] for row in candidates],
    }
    if CANDIDATE_PATH.exists():
        try:
            existing = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("F63 candidate identity file is corrupt") from exc
        if existing != candidate_payload:
            raise RuntimeError("F63 candidate identity file does not match frozen inputs")
    else:
        _atomic_json(CANDIDATE_PATH, candidate_payload)
    return gen1, teacher, candidates


def _resume_result_base(teacher: dict, gen1) -> dict:
    return {
        "work_order": RESUME_WORK_ORDER,
        "parent_repository_sha": RESUME_PARENT_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "teacher": {
            "status": "FROZEN_DECISION_ONLY",
            "artifact": str(TEACHER_DECISION_PATH.relative_to(ROOT)).replace("\\", "/"),
            "decision_state": teacher["bound"].decision_state,
            "decision_sufficient": teacher["bound"].decision_sufficient,
            "strength_estimate_complete": teacher["bound"].strength_estimate_complete,
        },
        "candidate_loop": {"status": "IDENTITIES_FROZEN"},
    }


def _read_resume_result() -> dict:
    try:
        result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "F63 resume stage prerequisite is missing or corrupt"
        ) from exc
    if result.get("work_order") != RESUME_WORK_ORDER:
        raise RuntimeError("F63 resume result belongs to another work order")
    return result


def _run_candidate_resume_stage(stage: str):
    if stage not in {"common-4", "selected-8", "selected-32"}:
        raise ValueError("F63 resume stage must be common-4, selected-8, or selected-32")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1, teacher, candidates = _resume_context(compiled)
    result = _resume_result_base(teacher, gen1)
    candidate_by_seed = {row["seed"]: row for row in candidates}

    if stage == "common-4":
        common = []
        for row in candidates:
            arena = _run_candidate_stage(
                compiled, native, gen1, row["checkpoint"], 4,
                COMMON_TRIAGE_SEED, f"candidate-{row['seed']}-common-4",
            )
            common.append({
                "seed": row["seed"],
                "checkpoint_id": row["identity"]["checkpoint_id"],
                "arena": arena,
            })
            if arena["status"] != "COMPLETE":
                result["candidate_loop"] = {
                    "status": "COMMON_INCOMPLETE_RESUMABLE",
                    "candidates": common,
                    "incomplete_stage": row["seed"],
                }
                _atomic_json(RESULT_PATH, result)
                return result
        result["candidate_loop"] = {
            "status": "COMMON_COMPLETE",
            "source_stage_identity_sha256": F62_STAGE_SHA,
            "records_sha256": F62_RECORDS_SHA,
            "candidates": common,
        }
        _atomic_json(RESULT_PATH, result)
        return result

    prior = _read_resume_result()
    prior_loop = prior.get("candidate_loop", {})
    if prior_loop.get("status") != "COMMON_COMPLETE":
        raise RuntimeError("F63 common-4 stage is not complete; selected stage is not eligible")
    selected = _select_candidate(prior_loop["candidates"])
    selected_row = candidate_by_seed[selected["seed"]]
    if stage == "selected-8":
        selected_eight = _run_candidate_stage(
            compiled, native, gen1, selected_row["checkpoint"], 8, 630404,
            f"selected-{selected['seed']}-8",
            stop_on_decision=True,
            decision_criterion="f63_teacher_gate",
        )
        result["candidate_loop"] = dict(prior_loop)
        result["candidate_loop"]["selected_seed"] = selected["seed"]
        result["candidate_loop"]["selected_checkpoint_id"] = selected["checkpoint_id"]
        result["candidate_loop"]["selected_8_pairs"] = selected_eight
        result["candidate_loop"]["selected_8_continuation"] = _selected_eight_continuation(
            selected_eight
        )
        _atomic_json(RESULT_PATH, result)
        return result

    selected_eight = prior_loop.get("selected_8_pairs")
    if not isinstance(selected_eight, dict):
        raise RuntimeError("F63 selected-8 stage is not complete")
    continuation = _selected_eight_continuation(selected_eight)
    if continuation != "RUN_32":
        raise RuntimeError(
            f"F63 selected-32 stage is not eligible after selected-8: {continuation}"
        )
    selected_32 = _run_candidate_stage(
        compiled, native, gen1, selected_row["checkpoint"], 32, 630405,
        f"selected-{selected['seed']}-32",
        decision_criterion="f63_teacher_gate",
    )
    result["candidate_loop"] = dict(prior_loop)
    result["candidate_loop"]["selected_32_pairs"] = selected_32
    if selected_32["status"] != "COMPLETE":
        result["candidate_loop"]["classification"] = (
            "CANDIDATE_CONFIRMATION_INCOMPLETE_RESUMABLE"
        )
    else:
        result["candidate_loop"]["classification"] = (
            "BOUNDED_CHAMPION_LOOP_REPEATABILITY_SIGNAL"
            if selected_32.get("bootstrap_low", 0.0) > 0.5
            else "TEACHER_IMPROVES_BUT_REPLACEMENT_DISTILLATION_FAILS"
        )
    _atomic_json(RESULT_PATH, result)
    return result


def run_candidate_resume(*, stage: str):
    """Run exactly one approved F63 candidate stage; never runs teacher games."""
    return _run_candidate_resume_stage(stage)


def run(*, smoke: bool = False):
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    result = {
        "work_order": WORK_ORDER,
        "parent_repository_sha": PARENT_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "teacher": {},
        "candidate_loop": {"status": "NOT_RUN"},
    }
    first_pairs, first_seed = TEACHER_STAGES[0]
    four = _run_teacher_stage(compiled, native, gen1, first_pairs, first_seed, smoke=smoke)
    result["teacher"]["4_pairs"] = four
    supported = _teacher_is_clearly_supported(four)
    if not supported:
        second_pairs, second_seed = TEACHER_STAGES[1]
        eight = _run_teacher_stage(compiled, native, gen1, second_pairs, second_seed, smoke=smoke)
        result["teacher"]["8_pairs"] = eight
        supported = (
            eight["mean_pair_score"] > 0.5
            and eight["child_better_pairs"] > eight["child_worse_pairs"]
        )
    result["teacher"]["classification"] = (
        "GEN1_SEARCH_POLICY_IMPROVEMENT_SUPPORTED"
        if supported else "GEN1_SEARCH_POLICY_IMPROVEMENT_UNRESOLVED_OR_FAILED"
    )
    if not supported or smoke:
        result["candidate_loop"]["status"] = (
            "NOT_RUN_TEACHER_GATE" if not supported else "SMOKE_ONLY"
        )
        _atomic_json(RESULT_PATH if not smoke else OUT / "f63_smoke_results.json", result)
        return result

    summary, provenance, persisted_gen2, persisted_identity = (
        _load_f62_training_summary(compiled, gen1)
    )
    candidates = []
    for seed in GEN2_SEEDS:
        if seed == 59012:
            candidate = persisted_gen2
            identity = persisted_identity | {
                "checkpoint_id": persisted_identity["gen2_checkpoint_id"],
                "reused_exact_f62_candidate": True,
            }
        else:
            candidate, identity = _fit_candidate(compiled, gen1, summary, provenance, seed)
        candidates.append({"seed": seed, "checkpoint": candidate, "identity": identity})
    _atomic_json(CANDIDATE_PATH, {
        "schema": "generic-chess-f63-candidates-v1",
        "source_stage_identity_sha256": F62_STAGE_SHA,
        "records_sha256": F62_RECORDS_SHA,
        "candidates": [row["identity"] for row in candidates],
    })
    common = []
    for row in candidates:
        common.append({
            "seed": row["seed"],
            "checkpoint_id": row["identity"]["checkpoint_id"],
            "arena": _run_candidate_stage(
                compiled, native, gen1, row["checkpoint"], 4,
                COMMON_TRIAGE_SEED, f"candidate-{row['seed']}-common-4",
            ),
        })
    selected = _select_candidate(common)
    result["candidate_loop"] = {
        "status": "RUN",
        "source_stage_identity_sha256": F62_STAGE_SHA,
        "records_sha256": F62_RECORDS_SHA,
        "candidates": common,
        "selected_seed": selected["seed"],
        "selected_checkpoint_id": selected["checkpoint_id"],
    }
    selected_candidate = next(
        row["checkpoint"] for row in candidates if row["seed"] == selected["seed"]
    )
    for pairs, seed in SELECTED_FRESH_SEEDS:
        result["candidate_loop"][f"selected_{pairs}_pairs"] = _run_candidate_stage(
            compiled, native, gen1, selected_candidate, pairs, seed,
            f"selected-{selected['seed']}-{pairs}",
        )
        if pairs == 8 and result["candidate_loop"]["selected_8_pairs"]["mean_pair_score"] < 0.5:
            break
    result["candidate_loop"]["classification"] = (
        "BOUNDED_CHAMPION_LOOP_REPEATABILITY_SIGNAL"
        if result["candidate_loop"].get("selected_32_pairs", {}).get("bootstrap_low", 0.0) > 0.5
        else "TEACHER_IMPROVES_BUT_REPLACEMENT_DISTILLATION_FAILS"
    )
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--resume-only", action="store_true",
        help="run only the frozen-teacher candidate resume path",
    )
    parser.add_argument(
        "--stage", choices=("common-4", "selected-8", "selected-32"),
        help="exactly one stage for the stage-scoped candidate resume path",
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.resume_only:
        if args.smoke or args.stage is None:
            raise SystemExit(
                "--resume-only requires exactly one explicit --stage and has no smoke mode"
            )
        result = run_candidate_resume(stage=args.stage)
    elif args.stage is not None:
        raise SystemExit("--stage is only valid with --resume-only")
    elif not args.smoke:
        raise SystemExit(
            "refusing unbounded F63 teacher entry; use --resume-only after compute approval"
        )
    else:
        result = run(smoke=True)
    print(json.dumps({
        "teacher_classification": result["teacher"]["classification"],
        "teacher_scores": {
            stage: payload["mean_pair_score"]
            for stage, payload in result["teacher"].items()
            if isinstance(payload, dict) and "mean_pair_score" in payload
        },
        "candidate_status": result["candidate_loop"]["status"],
        "candidate_classification": result["candidate_loop"].get("classification"),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
