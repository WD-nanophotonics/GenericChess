"""F79-R1 incremental Arena4 confirmation using frozen F78 prefix evidence."""

from __future__ import annotations

from dataclasses import asdict, replace
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
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f76_parent_retained_pointwise_q_output_delta as f76  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f79_parent_anchored_full_residual_arena4 as f79  # noqa: E402


WORK_ORDER = "GENERICCHESS-F79-R1-INCREMENTAL-FROZEN-ARENA4"
BASELINE_SHA = "b40be3aad27c157877dbffaa7d7b2c5e50fa2c82"
PARENT_SHA = f79.PARENT_SHA
CHILD_SHA = f79.CHILD_SHA
LABEL = f79.LABEL
F78_PREFIX_PAIR_SCORES = [0.5, 1.0]
SOURCE_OPENING_INDICES = (2, 3)
OPENING_SEED = f79.OPENING_SEED
OPENING_COUNT = 2
PAIRS = 2
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
F78_RESULT = ROOT / ".generic_chess_flow" / "f78-parent-anchored-full-residual-arena2" / "f78_results.json"
F78_OPENINGS = f79.F78_OPENINGS
OUT = ROOT / ".generic_chess_flow" / "f79-r1-incremental-frozen-arena4-corrected"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f79_r1_results.json"


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_frozen_openings(compiled):
    payload = json.loads(F78_OPENINGS.read_text(encoding="utf-8"))
    corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
    corpus.validate(compiled)
    selected = tuple(opening for opening in corpus.openings if opening.index in SOURCE_OPENING_INDICES)
    if len(selected) != len(SOURCE_OPENING_INDICES) or tuple(o.index for o in selected) != SOURCE_OPENING_INDICES:
        raise RuntimeError("F79-R1 source opening index selection mismatch")
    subset = ArenaOpeningCorpus(
        schema_version=corpus.schema_version,
        ruleset_fingerprint=corpus.ruleset_fingerprint,
        seed=corpus.seed,
        min_plies=corpus.min_plies,
        max_plies=corpus.max_plies,
        # The arena progress schema uses local pair indices for game identity.
        # Retain the durable source indices in the result metadata while
        # reindexing this two-opening view only for the local scheduler.
        openings=tuple(replace(opening, index=local_index) for local_index, opening in enumerate(selected)),
    )
    return subset, {
        "source_path": str(F78_OPENINGS.relative_to(ROOT)),
        "source_corpus_id": corpus.corpus_id,
        "source_opening_indices": list(SOURCE_OPENING_INDICES),
        "source_final_position_keys": [opening.final_position_key for opening in selected],
        "source_seed": corpus.seed,
        "selected_subset_id": subset.corpus_id,
    }


def _load_frozen_pair_prefix():
    payload = json.loads(F78_RESULT.read_text(encoding="utf-8"))
    summary = payload["arena"]["summary"]
    if payload["parent_checkpoint_id"] != PARENT_SHA or payload["child_checkpoint_id"] != CHILD_SHA:
        raise RuntimeError("F79-R1 F78 prefix checkpoint identity mismatch")
    if summary["pair_scores"] != F78_PREFIX_PAIR_SCORES:
        raise RuntimeError("F79-R1 F78 prefix pair-score mismatch")
    if summary["pair_count"] != 2 or summary["game_wins"] != 3 or summary["game_draws"] != 0 or summary["game_losses"] != 1:
        raise RuntimeError("F79-R1 F78 prefix W/D/L mismatch")
    return summary


def _run_incremental(compiled, native, gen1, candidate, openings):
    config = ArenaConfig(
        pairs=PAIRS, nodes_per_move=NODES, parent_nodes_per_move=NODES,
        child_nodes_per_move=NODES, max_depth=MAX_DEPTH,
        tt_megabytes=TT_MEGABYTES, opening_seed=OPENING_SEED,
        opening_count=OPENING_COUNT, min_plies=2, max_plies=6, workers=1,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=3600, per_game_nodes=131072,
        per_game_plies=256, max_stage_games=4, max_concurrent_games=1,
        stage_wall_seconds=3600,
    )
    first = run_arena_game_resumable(
        compiled, native, gen1, candidate, config, progress_dir=PROGRESS,
        openings=openings, capture_search_metrics=True, caps=caps,
        stage_id="f79-r1-incremental-arena4",
    )
    replay = run_arena_game_resumable(
        compiled, native, gen1, candidate, config, progress_dir=PROGRESS,
        openings=openings, capture_search_metrics=True, caps=caps,
        stage_id="f79-r1-incremental-arena4",
    )
    summary = f77._summary_payload(first)
    replay_summary = f77._summary_payload(replay)
    telemetry = f77._telemetry(first) if first is not None else {}
    failures = []
    if summary is not None and summary["pair_count"] != 2:
        failures.append("incremental summary does not contain two pairs")
    if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs:
        failures.append("incremental replay status or counts differ")
    if summary != replay_summary:
        failures.append("incremental replay summary differs")
    if telemetry and not telemetry.get("all_root_window_pruning_true", False):
        failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        failures.append("root pruning telemetry field was missing")
    return {
        "config": {
            "pairs": PAIRS, "total_games": 4, "source_opening_indices": list(SOURCE_OPENING_INDICES),
            "nodes_per_move": NODES, "parent_nodes_per_move": NODES,
            "child_nodes_per_move": NODES, "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES, "workers": 1,
            "root_window_pruning": True, "execution_caps": asdict(caps),
        },
        "run": {
            "status": first.status, "completed_games": first.completed_games,
            "completed_pairs": first.completed_pairs, "total_games": first.total_games,
            "reason": first.reason, "effective_game_lanes": first.effective_game_lanes,
        },
        "summary": summary,
        "telemetry": telemetry,
        "replay_validation": {
            "status": replay.status, "completed_games": replay.completed_games,
            "completed_pairs": replay.completed_pairs, "summary_equal": summary == replay_summary,
        },
        "contract_failures": failures,
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F79-R1 requires the native extension")
    prefix = _load_frozen_pair_prefix()
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1, candidate, descriptor = f79._load_frozen_candidate(compiled)
    openings, opening_payload = _load_frozen_openings(compiled)
    incremental = _run_incremental(compiled, native, gen1, candidate, openings)
    failures = list(incremental["contract_failures"])
    summary = incremental["summary"]
    if incremental["run"]["status"] == "COMPLETE" and incremental["run"]["completed_games"] != 4:
        failures.append("complete incremental stage does not contain four games")
    if incremental["run"]["status"] == "COMPLETE" and incremental["run"]["completed_pairs"] != 2:
        failures.append("complete incremental stage does not contain two pairs")
    aggregate_scores = F78_PREFIX_PAIR_SCORES + ([] if summary is None else list(summary["pair_scores"]))
    aggregate = None
    if summary is not None:
        low, high = bootstrap_pair_mean_ci(aggregate_scores)
        aggregate = {
            "pair_count": len(aggregate_scores), "pair_scores": aggregate_scores,
            "mean_pair_score": sum(aggregate_scores) / len(aggregate_scores),
            "child_better_pairs": prefix["child_better_pairs"] + summary["child_better_pairs"],
            "tied_pairs": prefix["tied_pairs"] + summary["tied_pairs"],
            "child_worse_pairs": prefix["child_worse_pairs"] + summary["child_worse_pairs"],
            "bootstrap_low": low, "bootstrap_high": high,
            "game_wins": prefix["game_wins"] + summary["game_wins"],
            "game_draws": prefix["game_draws"] + summary["game_draws"],
            "game_losses": prefix["game_losses"] + summary["game_losses"],
        }
    if failures:
        classification = "HARNESS_MISMATCH"
    elif incremental["run"]["status"] != "COMPLETE":
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_UNRESOLVED"
    elif aggregate["mean_pair_score"] > 0.5 and aggregate["child_better_pairs"] > aggregate["child_worse_pairs"]:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES"
    else:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_REJECTED"
    result = {
        "schema": "generic-chess-f79-r1-incremental-frozen-arena4-v1",
        "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA,
        "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": descriptor["candidate_model_sha256"],
        "opening_corpus": opening_payload, "f78_prefix": {
            "pair_scores": F78_PREFIX_PAIR_SCORES,
            "game_wins": prefix["game_wins"], "game_draws": prefix["game_draws"], "game_losses": prefix["game_losses"],
        },
        "incremental": incremental, "aggregate_four_pair_gate": aggregate,
        "contract_failures": failures,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ("scripts/f79_r1_incremental_frozen_arena4.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    aggregate = result["aggregate_four_pair_gate"] or {}
    print(json.dumps({
        "classification": result["classification"],
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "child_checkpoint_id": result["child_checkpoint_id"],
        "f78_prefix_pair_scores": result["f78_prefix"]["pair_scores"],
        "incremental_pair_scores": (result["incremental"]["summary"] or {}).get("pair_scores"),
        "aggregate_pair_scores": aggregate.get("pair_scores"),
        "aggregate_mean_pair_score": aggregate.get("mean_pair_score"),
        "game_wins": aggregate.get("game_wins"), "game_draws": aggregate.get("game_draws"),
        "game_losses": aggregate.get("game_losses"),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
