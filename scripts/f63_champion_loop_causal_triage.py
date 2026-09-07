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

from generic_chess.learning.arena import ArenaConfig, run_arena_resumable
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


def _run_candidate_stage(compiled, native, gen1, candidate, pairs, seed, label):
    openings = generate_arena_openings(
        compiled, count=pairs, seed=seed, min_plies=2, max_plies=6
    )
    summary = run_arena_resumable(
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
    )
    return _arena_payload(summary)


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
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    result = run(smoke=args.smoke)
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
