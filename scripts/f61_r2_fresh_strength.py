"""Fresh-opening, crash-resumable Arena certification for corrected F61."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, run_arena_resumable
from generic_chess.learning.openings import generate_arena_openings
from generic_chess.learning.serialization import stable_sha256
from scripts import f59_action_spectrum_diagnosis as f59
from scripts.f61_strength_first_triage import _arena_payload, _search_validation


WORK_ORDER = "GENERICCHESS-F61-CORRECTIVE-R2-PERSPECTIVE-CERTIFICATION-AND-FRESH-STRENGTH"
OUTPUT_DIR = ROOT / ".generic_chess_flow" / "f61-strength-first-triage"
PROGRESS_DIR = OUTPUT_DIR / "f61-r2-progress"
PARTIAL_PATH = OUTPUT_DIR / "f61_r2_partial.json"
RESULT_PATH = OUTPUT_DIR / "f61_r2_results.json"
STAGE_MANIFEST_PATH = PROGRESS_DIR / "stage-manifest.json"
NODES_PER_MOVE = 2000
CORRECTED_TRAINING_CONFIG = "f61-corrected-perspective"
EXPECTED_CORRECTED_IDS = {
    "F60_D0_PAIRWISE_SEED_59012":
        "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4",
    "F60_D12_MEDIAN_DEVELOPMENT_SEED":
        "da51634c07eaa86b300e6e7c7e563bb79c002218156ec49900fc3dc1a32946d3",
    "F60_D2_MEDIAN_DEVELOPMENT_SEED":
        "3bc950ed46b483f09852de56d1d942505b04ac2ca9aeacd1ea40f5cae1825f29",
}


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _workers(unit_count: int, *, concurrent_lanes: int = 1) -> int:
    available = max(1, os.cpu_count() or 1)
    return max(1, min(unit_count, available // max(1, concurrent_lanes)))


def _candidate_checkpoint(parent, candidate):
    return parent.child_checkpoint(
        board_weights=parent.board_weights,
        hand_weights=parent.hand_weights,
        dynamic_weights=parent.dynamic_weights,
        compact_nonlinear=candidate["model"],
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=CORRECTED_TRAINING_CONFIG,
        training_seed=candidate["seed"],
    )


def _validation_is_reusable(row, candidate, child, openings) -> bool:
    """Validate a complete validation unit before importing it."""
    if not isinstance(row, dict) or row.get("candidate_id") != candidate["candidate_id"]:
        return False
    if row.get("old_checkpoint_id") != candidate["checkpoint_id"]:
        return False
    if row.get("corrected_checkpoint_id") != child.checkpoint_id:
        return False
    validation = row.get("search_validation")
    if (
        not isinstance(validation, dict)
        or validation.get("opening_count") != len(openings.openings)
    ):
        return False
    rows = validation.get("rows")
    if not isinstance(rows, list) or len(rows) != len(openings.openings):
        return False
    expected_ids = [opening.final_position_key for opening in openings.openings]
    if [item.get("opening_id") for item in rows if isinstance(item, dict)] != expected_ids:
        return False
    if any(
        item.get("parent_nodes") != NODES_PER_MOVE
        or item.get("child_nodes") != NODES_PER_MOVE
        or not isinstance(item.get("decision_changed"), bool)
        for item in rows
    ):
        return False
    return validation.get("decision_changes") == sum(
        item["decision_changed"] for item in rows
    )


def _load_reusable_validations(path, candidates, checkpoints, corpora):
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    available = {
        row.get("candidate_id"): row
        for row in payload.get("candidates", [])
        if isinstance(row, dict)
    }
    reusable = {}
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        row = available.get(candidate_id)
        if _validation_is_reusable(
            row, candidate, checkpoints[candidate_id], corpora[candidate_id]
        ):
            reusable[candidate_id] = row["search_validation"]
    return reusable


def _validation_identity(candidate, child, openings):
    identity = {
        "candidate_id": candidate["candidate_id"],
        "old_checkpoint_id": candidate["checkpoint_id"],
        "corrected_checkpoint_id": child.checkpoint_id,
        "nodes_per_side": NODES_PER_MOVE,
        "ordered_opening_ids": [
            opening.final_position_key for opening in openings.openings
        ],
    }
    return identity, stable_sha256(identity)


def _load_validation_unit(path, candidate, child, openings):
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"F61 validation unit is corrupt: {path}") from exc
    identity, identity_sha256 = _validation_identity(candidate, child, openings)
    if (
        payload.get("schema") != "generic-chess-f61-r2-validation-v1"
        or payload.get("identity") != identity
        or payload.get("identity_sha256") != identity_sha256
    ):
        raise RuntimeError(f"F61 validation unit identity mismatch: {path}")
    row = {
        "candidate_id": candidate["candidate_id"],
        "old_checkpoint_id": candidate["checkpoint_id"],
        "corrected_checkpoint_id": child.checkpoint_id,
        "search_validation": payload.get("validation"),
    }
    if not _validation_is_reusable(row, candidate, child, openings):
        raise RuntimeError(f"F61 validation unit is incomplete: {path}")
    return payload["validation"]


def _write_validation_unit(path, candidate, child, openings, validation):
    identity, identity_sha256 = _validation_identity(candidate, child, openings)
    _atomic_json(path, {
        "schema": "generic-chess-f61-r2-validation-v1",
        "identity": identity,
        "identity_sha256": identity_sha256,
        "validation": validation,
    })


def _stage_manifest(compiled, parent, candidates, checkpoints):
    identity = {
        "work_order": WORK_ORDER,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "parent_checkpoint_id": parent.checkpoint_id,
        "nodes_per_move": NODES_PER_MOVE,
        "max_depth": 12,
        "tt_megabytes": 8,
        "min_plies": 2,
        "max_plies": 6,
        "candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "old_checkpoint_id": candidate["checkpoint_id"],
                "corrected_checkpoint_id": checkpoints[candidate["candidate_id"]].checkpoint_id,
                "validation_seed": 620701 + index,
                "validation_openings": 8,
                "arena_4_seed": 620701 + index,
            }
            for index, candidate in enumerate(candidates)
        ],
        "best_stages": [
            {"pairs": 8, "opening_seed": 620801},
            {"pairs": 32, "opening_seed": 620802},
        ],
    }
    return {
        "schema": "generic-chess-f61-r2-stage-v1",
        "identity_sha256": stable_sha256(identity),
        "identity": identity,
    }


def _ensure_stage_manifest(expected):
    if STAGE_MANIFEST_PATH.is_file():
        try:
            actual = json.loads(STAGE_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("F61 R2 stage manifest is corrupt") from exc
        if actual != expected:
            raise RuntimeError("F61 R2 stage manifest identity mismatch")
    else:
        _atomic_json(STAGE_MANIFEST_PATH, expected)


def _arena_config(pairs, seed, *, concurrent_lanes=1):
    return ArenaConfig(
        pairs=pairs,
        nodes_per_move=NODES_PER_MOVE,
        max_depth=12,
        tt_megabytes=8,
        opening_seed=seed,
        opening_count=pairs,
        min_plies=2,
        max_plies=6,
        workers=_workers(pairs, concurrent_lanes=concurrent_lanes),
    )


def _run_stage(
    compiled, native, parent, child, candidate_id, pairs, seed, *, concurrent_lanes=1
):
    openings = generate_arena_openings(
        compiled, count=pairs, seed=seed, min_plies=2, max_plies=6
    )
    return run_arena_resumable(
        compiled, native, parent, child,
        _arena_config(pairs, seed, concurrent_lanes=concurrent_lanes),
        progress_dir=PROGRESS_DIR / candidate_id / f"arena-{pairs}-seed-{seed}",
        openings=openings,
    )


def main() -> None:
    data = json.loads(
        (ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json")
        .read_text(encoding="utf-8")
    )
    candidates = data["corrected_candidates"]
    compiled, native, _ = f59._ruleset(f59.LABELS[1])
    parent = f59._parent(f59.LABELS[1])
    checkpoints = {
        candidate["candidate_id"]: _candidate_checkpoint(parent, candidate)
        for candidate in candidates
    }
    actual_ids = {
        candidate_id: checkpoint.checkpoint_id
        for candidate_id, checkpoint in checkpoints.items()
    }
    if actual_ids != EXPECTED_CORRECTED_IDS:
        raise RuntimeError("corrected F61 checkpoint identities do not match the work order")
    corpora = {
        candidate["candidate_id"]: generate_arena_openings(
            compiled, count=8, seed=620701 + index, min_plies=2, max_plies=6
        )
        for index, candidate in enumerate(candidates)
    }
    _ensure_stage_manifest(_stage_manifest(compiled, parent, candidates, checkpoints))
    reusable = _load_reusable_validations(
        PARTIAL_PATH, candidates, checkpoints, corpora
    )

    candidate_lanes = _workers(len(candidates))

    def evaluate_candidate(index, candidate):
        candidate_id = candidate["candidate_id"]
        child = checkpoints[candidate_id]
        openings = corpora[candidate_id]
        validation_path = PROGRESS_DIR / candidate_id / "validation.json"
        validation = _load_validation_unit(
            validation_path, candidate, child, openings
        ) or reusable.get(candidate_id)
        if validation is None:
            with ThreadPoolExecutor(max_workers=_workers(
                len(openings.openings), concurrent_lanes=candidate_lanes
            )) as pool:
                validation_rows = list(pool.map(
                    lambda opening: _search_validation(
                        compiled, native, parent, child,
                        type("Openings", (), {"openings": (opening,)})(),
                        NODES_PER_MOVE,
                    )["rows"][0],
                    openings.openings,
                ))
            validation = {
                "opening_count": len(validation_rows),
                "decision_changes": sum(row["decision_changed"] for row in validation_rows),
                "first_decision_divergence": next(
                    (row for row in validation_rows if row["decision_changed"]), None
                ),
                "rows": validation_rows,
            }
        _write_validation_unit(
            validation_path, candidate, child, openings, validation
        )
        row = {
            "candidate_id": candidate_id,
            "corrected_checkpoint_id": child.checkpoint_id,
            "old_checkpoint_id": candidate["checkpoint_id"],
            "first_decision_divergence": next(
                (item for item in validation["rows"] if item["decision_changed"]), None
            ),
            "search_validation": validation,
        }
        if validation["decision_changes"]:
            row["arena_4_pairs"] = _arena_payload(_run_stage(
                compiled, native, parent, child, candidate_id, 4, 620701 + index,
                concurrent_lanes=candidate_lanes,
            ))
        return index, row

    completed_rows = {}
    with ThreadPoolExecutor(max_workers=candidate_lanes) as pool:
        futures = {
            pool.submit(evaluate_candidate, index, candidate): index
            for index, candidate in enumerate(candidates)
        }
        for future in as_completed(futures):
            index, row = future.result()
            completed_rows[index] = row
            _atomic_json(PARTIAL_PATH, {
                "stage": "candidate_4_pairs",
                "candidates": [completed_rows[i] for i in sorted(completed_rows)],
            })
    rows = [completed_rows[index] for index in range(len(candidates))]

    active = [row for row in rows if "arena_4_pairs" in row]
    best = max(active, key=lambda row: row["arena_4_pairs"]["mean_pair_score"]) if active else None
    if best is not None:
        child = checkpoints[best["candidate_id"]]
        for pairs, seed in ((8, 620801), (32, 620802)):
            best[f"arena_{pairs}_pairs"] = _arena_payload(_run_stage(
                compiled, native, parent, child, best["candidate_id"], pairs, seed
            ))
            _atomic_json(PARTIAL_PATH, {
                "stage": f"candidate_{pairs}_pairs",
                "candidates": rows,
                "best_candidate_id": best["candidate_id"],
            })

    result = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": parent.checkpoint_id,
        "fresh_opening_seeds": [620701, 620801, 620802],
        "candidates": rows,
        "best_candidate_id": None if best is None else best["candidate_id"],
        "teacher_metrics_are_diagnostic_only": True,
    }
    _atomic_json(RESULT_PATH, result)
    print(json.dumps({
        "best_candidate_id": result["best_candidate_id"],
        "candidates": [
            {
                "id": row["candidate_id"],
                "mean4": row.get("arena_4_pairs", {}).get("mean_pair_score"),
                "mean8": row.get("arena_8_pairs", {}).get("mean_pair_score"),
                "mean32": row.get("arena_32_pairs", {}).get("mean_pair_score"),
            }
            for row in rows
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
