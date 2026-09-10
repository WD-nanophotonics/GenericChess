"""F80 incremental Arena8 stage over the remaining frozen openings."""

from __future__ import annotations

from dataclasses import replace, asdict
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.learning.statistics import bootstrap_pair_mean_ci  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f79_parent_anchored_full_residual_arena4 as f79  # noqa: E402


WORK_ORDER = "GENERICCHESS-F80-INCREMENTAL-FROZEN-ARENA8"
BASELINE_SHA = "afbc265c282c4fff091db959b931d6515a9662dc"
PARENT_SHA = f79.PARENT_SHA
CHILD_SHA = f79.CHILD_SHA
CANDIDATE_MODEL_SHA = "b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6"
CORPUS_ID = "2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48"
F78_OPENINGS = f79.F78_OPENINGS
F79_EVIDENCE = ROOT / "artifacts" / "f79_parent_anchored_full_residual" / "arena4_strength_evidence.json"
SOURCE_OPENING_INDICES = (4, 5, 6, 7)
OPENING_SEED = 780501
OPENING_COUNT = 4
PAIRS = 4
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
OUT = ROOT / ".generic_chess_flow" / "f80-incremental-frozen-arena8"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f80_results.json"


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_prefix():
    payload = json.loads(F79_EVIDENCE.read_text(encoding="utf-8"))
    if hashlib.sha256(F79_EVIDENCE.read_bytes()).hexdigest() != "888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477":
        raise RuntimeError("F80 Arena4 evidence content SHA mismatch")
    if payload["parent_checkpoint_id"] != PARENT_SHA or payload["child_checkpoint_id"] != CHILD_SHA:
        raise RuntimeError("F80 prefix checkpoint identity mismatch")
    if payload["candidate_model_sha256"] != CANDIDATE_MODEL_SHA or payload["corpus_id"] != CORPUS_ID:
        raise RuntimeError("F80 prefix model or corpus identity mismatch")
    if payload["prefix_source_opening_indices"] != [0, 1] or payload["incremental_source_opening_indices"] != [2, 3]:
        raise RuntimeError("F80 prefix source opening mapping mismatch")
    if payload["combined_pair_scores"] != [0.5, 1.0, 0.5, 0.5] or payload["combined_completed_games"] != 8 or payload["combined_completed_pairs"] != 4:
        raise RuntimeError("F80 durable Arena4 prefix mismatch")
    if payload["classification"] != "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES":
        raise RuntimeError("F80 durable Arena4 prefix classification mismatch")
    return payload


def _load_remaining_openings(compiled):
    payload = json.loads(F78_OPENINGS.read_text(encoding="utf-8"))
    corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
    corpus.validate(compiled)
    if corpus.corpus_id != CORPUS_ID or payload["corpus_id"] != CORPUS_ID:
        raise RuntimeError("F80 source corpus identity mismatch")
    selected = tuple(opening for opening in corpus.openings if opening.index in SOURCE_OPENING_INDICES)
    if tuple(opening.index for opening in selected) != SOURCE_OPENING_INDICES:
        raise RuntimeError("F80 remaining source opening selection mismatch")
    subset = replace(corpus, openings=tuple(replace(opening, index=local_index) for local_index, opening in enumerate(selected)))
    return subset, {
        "source_corpus_id": corpus.corpus_id,
        "source_opening_indices": list(SOURCE_OPENING_INDICES),
        "source_final_position_keys": [opening.final_position_key for opening in selected],
        "local_to_source_index": {str(local): source for local, source in enumerate(SOURCE_OPENING_INDICES)},
        "selected_subset_id": subset.corpus_id,
        "source_seed": corpus.seed,
    }


def _run_incremental(compiled, native, gen1, candidate, openings):
    config = ArenaConfig(
        pairs=PAIRS, nodes_per_move=NODES, parent_nodes_per_move=NODES,
        child_nodes_per_move=NODES, max_depth=MAX_DEPTH,
        tt_megabytes=TT_MEGABYTES, opening_seed=OPENING_SEED,
        opening_count=OPENING_COUNT, min_plies=2, max_plies=6, workers=2,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=3600, per_game_nodes=131072,
        per_game_plies=256, max_stage_games=8, max_concurrent_games=2,
        stage_wall_seconds=3600,
    )
    first = run_arena_game_resumable(
        compiled, native, gen1, candidate, config, progress_dir=PROGRESS,
        openings=openings, capture_search_metrics=True, caps=caps,
        stage_id="f80-incremental-arena8",
    )
    replay = run_arena_game_resumable(
        compiled, native, gen1, candidate, config, progress_dir=PROGRESS,
        openings=openings, capture_search_metrics=True, caps=caps,
        stage_id="f80-incremental-arena8",
    )
    summary = f77._summary_payload(first.summary)
    replay_summary = f77._summary_payload(replay.summary)
    telemetry = f77._telemetry(first.summary) if first.summary is not None else {}
    failures = []
    if first.status == "COMPLETE" and (replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs):
        failures.append("incremental replay status or counts differ")
    if first.status == "COMPLETE" and summary != replay_summary:
        failures.append("incremental replay summary differs")
    if telemetry and not telemetry.get("all_root_window_pruning_true", False):
        failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        failures.append("root pruning telemetry field was missing")
    if first.effective_game_lanes != 2:
        failures.append("effective game lanes did not equal two")
    return {
        "config": {
            "pairs": PAIRS, "total_games": 8, "source_opening_indices": list(SOURCE_OPENING_INDICES),
            "nodes_per_move": NODES, "parent_nodes_per_move": NODES,
            "child_nodes_per_move": NODES, "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES, "workers": 2,
            "root_window_pruning": True, "execution_caps": asdict(caps),
        },
        "run": {
            "status": first.status, "completed_games": first.completed_games,
            "completed_pairs": first.completed_pairs, "total_games": first.total_games,
            "reason": first.reason, "effective_game_lanes": first.effective_game_lanes,
        },
        "summary": summary, "telemetry": telemetry,
        "replay_validation": {
            "status": replay.status, "completed_games": replay.completed_games,
            "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary,
        },
        "contract_failures": failures,
    }


def _normalize_existing_cap_result() -> dict:
    """Normalize a completed raw run after a cap without scheduling more games."""
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    run = result["incremental"]["run"]
    if run["status"] == "COMPLETE" or not run.get("reason"):
        raise RuntimeError("F80 existing result is not an incomplete capped run")
    result["classification"] = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_UNRESOLVED"
    result["contract_failures"] = []
    result["incremental"]["contract_failures"] = []
    result["normalization"] = "cap_result_only; no games scheduled"
    result["code_provenance"]["scripts/f80_incremental_frozen_arena8.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    _atomic_json(RESULT_PATH, result)
    return result


def run() -> dict:
    if not native_available():
        raise RuntimeError("F80 requires the native extension")
    prefix = _load_prefix()
    compiled, native, _profile = f79.f59._ruleset(f79.LABEL)
    gen1, candidate, descriptor = f79._load_frozen_candidate(compiled)
    openings, opening_payload = _load_remaining_openings(compiled)
    incremental = _run_incremental(compiled, native, gen1, candidate, openings)
    failures = list(incremental["contract_failures"])
    summary = incremental["summary"]
    if incremental["run"]["status"] == "COMPLETE" and (incremental["run"]["completed_games"] != 8 or incremental["run"]["completed_pairs"] != 4):
        failures.append("complete incremental stage does not contain eight games and four pairs")
    combined_scores = prefix["combined_pair_scores"] + ([] if summary is None else list(summary["pair_scores"]))
    aggregate = None
    if summary is not None:
        low, high = bootstrap_pair_mean_ci(combined_scores)
        aggregate = {
            "pair_count": len(combined_scores), "pair_scores": combined_scores,
            "mean_pair_score": sum(combined_scores) / len(combined_scores),
            "child_better_pairs": prefix["combined_child_better_pairs"] + summary["child_better_pairs"],
            "tied_pairs": prefix["combined_tied_pairs"] + summary["tied_pairs"],
            "child_worse_pairs": prefix["combined_child_worse_pairs"] + summary["child_worse_pairs"],
            "bootstrap_low": low, "bootstrap_high": high,
            "game_wins": prefix["combined_game_wins"] + summary["game_wins"],
            "game_draws": prefix["combined_game_draws"] + summary["game_draws"],
            "game_losses": prefix["combined_game_losses"] + summary["game_losses"],
            "completed_games": prefix["combined_completed_games"] + incremental["run"]["completed_games"],
            "completed_pairs": prefix["combined_completed_pairs"] + incremental["run"]["completed_pairs"],
        }
    if failures:
        classification = "HARNESS_MISMATCH"
    elif incremental["run"]["status"] != "COMPLETE":
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_UNRESOLVED"
    elif aggregate["mean_pair_score"] > 0.5 and aggregate["child_better_pairs"] > aggregate["child_worse_pairs"]:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_SURVIVES"
    else:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_REJECTED"
    result = {
        "schema": "generic-chess-f80-incremental-frozen-arena8-v1",
        "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA,
        "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": descriptor["candidate_model_sha256"],
        "prefix_arena4_evidence": {"path": str(F79_EVIDENCE.relative_to(ROOT)), "content_sha256": hashlib.sha256(F79_EVIDENCE.read_bytes()).hexdigest()},
        "opening_corpus": opening_payload, "incremental": incremental,
        "aggregate_arena8": aggregate, "contract_failures": failures,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ("scripts/f80_incremental_frozen_arena8.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = _normalize_existing_cap_result() if len(sys.argv) == 2 and sys.argv[1] == "--normalize-existing" else run()
    aggregate = result["aggregate_arena8"] or {}
    print(json.dumps({
        "classification": result["classification"],
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "child_checkpoint_id": result["child_checkpoint_id"],
        "incremental_pair_scores": (result["incremental"]["summary"] or {}).get("pair_scores"),
        "aggregate_pair_scores": aggregate.get("pair_scores"),
        "aggregate_mean_pair_score": aggregate.get("mean_pair_score"),
        "game_wins": aggregate.get("game_wins"), "game_draws": aggregate.get("game_draws"),
        "game_losses": aggregate.get("game_losses"),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
