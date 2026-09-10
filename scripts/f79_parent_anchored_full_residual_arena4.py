"""F79 frozen F78 candidate replay and four-pair Arena4 triage."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f76_parent_retained_pointwise_q_output_delta as f76  # noqa: E402
from scripts import f77_trusted_pointwise_q_arena2_triage as f77  # noqa: E402
from scripts import f78_parent_anchored_full_residual_arena2 as f78  # noqa: E402


WORK_ORDER = "GENERICCHESS-F79-PARENT-ANCHORED-FULL-RESIDUAL-ARENA4"
BASELINE_SHA = "322121b5f987439d5606e93b7974067ad88b1a6c"
PARENT_SHA = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
CHILD_SHA = "f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = PARENT_SHA
F78_CANDIDATE = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "candidate.json"
F78_OPENINGS = ROOT / "artifacts" / "f78_parent_anchored_full_residual" / "openings.json"
OUT = ROOT / ".generic_chess_flow" / "f79-parent-anchored-full-residual-arena4"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f79_results.json"
CORPUS_ID = "2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48"
OPENING_SEED = 780501
OPENING_COUNT = 8
PAIRS = 4
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8
F78_FIRST_TWO_PAIR_SCORES = [0.5, 1.0]


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_frozen_candidate(compiled):
    descriptor = json.loads(F78_CANDIDATE.read_text(encoding="utf-8"))
    identity = descriptor["canonical_training_identity"]
    model = CompactNonlinearResidual.from_dict(descriptor["final_compact_nonlinear"])
    if stable_sha256(model.to_dict()) != descriptor["candidate_model_sha256"]:
        raise RuntimeError("F79 candidate model SHA mismatch")
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), next(
        item for item in json.loads(
            (ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json").read_text(encoding="utf-8")
        )["corrected_candidates"] if item["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012"
    ))
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F79 parent checkpoint identity mismatch")
    gen1.validate_ruleset(compiled)
    candidate, training_hash = f78._make_candidate(gen1, model, identity)
    if candidate.checkpoint_id != CHILD_SHA or descriptor["child_checkpoint_id"] != CHILD_SHA:
        raise RuntimeError("F79 child checkpoint identity mismatch")
    if training_hash != descriptor["training_config_hash"]:
        raise RuntimeError("F79 training configuration hash mismatch")
    round_trip = candidate.from_dict(candidate.to_dict())
    if round_trip.checkpoint_id != CHILD_SHA:
        raise RuntimeError("F79 candidate checkpoint round trip mismatch")
    candidate.validate_ruleset(compiled)
    return gen1, candidate, descriptor


def _load_frozen_openings(compiled):
    payload = json.loads(F78_OPENINGS.read_text(encoding="utf-8"))
    corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
    corpus.validate(compiled)
    if payload.get("corpus_id") != CORPUS_ID or corpus.corpus_id != CORPUS_ID:
        raise RuntimeError("F79 frozen opening corpus identity mismatch")
    if payload["corpus"]["seed"] != OPENING_SEED or len(corpus.openings) != OPENING_COUNT:
        raise RuntimeError("F79 frozen opening corpus shape mismatch")
    return corpus, {"path": str(F78_OPENINGS.relative_to(ROOT)), "corpus_id": CORPUS_ID, "seed": OPENING_SEED, "opening_count": OPENING_COUNT}


def _run_arena(compiled, native, gen1, candidate, openings):
    config = ArenaConfig(
        pairs=PAIRS,
        nodes_per_move=NODES,
        parent_nodes_per_move=NODES,
        child_nodes_per_move=NODES,
        max_depth=MAX_DEPTH,
        tt_megabytes=TT_MEGABYTES,
        opening_seed=OPENING_SEED,
        opening_count=OPENING_COUNT,
        min_plies=2,
        max_plies=6,
        workers=1,
    )
    caps = ArenaExecutionCaps(
        per_game_wall_seconds=3600,
        per_game_nodes=131072,
        per_game_plies=256,
        max_stage_games=8,
        max_concurrent_games=4,
        stage_wall_seconds=3600,
    )
    first = run_arena_game_resumable(
        compiled, native, gen1, candidate, config,
        progress_dir=PROGRESS, openings=openings, capture_search_metrics=True,
        caps=caps, stage_id="f79-arena4",
    )
    replay = run_arena_game_resumable(
        compiled, native, gen1, candidate, config,
        progress_dir=PROGRESS, openings=openings, capture_search_metrics=True,
        caps=caps, stage_id="f79-arena4",
    )
    summary = f77._summary_payload(first.summary)
    replay_summary = f77._summary_payload(replay.summary)
    telemetry = f77._telemetry(first.summary) if first.summary is not None else {}
    contract_failures = []
    if first.status == "COMPLETE" and first.completed_games != 8:
        contract_failures.append("complete stage does not contain eight games")
    if first.status == "COMPLETE" and first.completed_pairs != 4:
        contract_failures.append("complete stage does not contain four pairs")
    if summary is not None and list(summary["pair_scores"][:2]) != F78_FIRST_TWO_PAIR_SCORES:
        contract_failures.append("first two pair scores do not reproduce F78")
    if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs:
        contract_failures.append("progress replay status or counts differ")
    if summary != replay_summary:
        contract_failures.append("progress replay summary differs")
    if telemetry and not telemetry.get("all_root_window_pruning_true", False):
        contract_failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        contract_failures.append("root pruning telemetry field was missing")
    return {
        "config": {
            "pairs": PAIRS, "total_games": 8, "nodes_per_move": NODES,
            "parent_nodes_per_move": NODES, "child_nodes_per_move": NODES,
            "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "workers": 1,
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
        "contract_failures": contract_failures,
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F79 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1, candidate, descriptor = _load_frozen_candidate(compiled)
    openings, opening_payload = _load_frozen_openings(compiled)
    arena = _run_arena(compiled, native, gen1, candidate, openings)
    failures = list(arena["contract_failures"])
    run_info = arena["run"]
    summary = arena["summary"]
    if failures:
        classification = "HARNESS_MISMATCH"
    elif run_info["status"] != "COMPLETE":
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_UNRESOLVED"
    elif summary["mean_pair_score"] > 0.5 and summary["child_better_pairs"] > summary["child_worse_pairs"]:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_SURVIVES"
    else:
        classification = "PARENT_ANCHORED_FULL_RESIDUAL_ARENA4_REJECTED"
    result = {
        "schema": "generic-chess-f79-parent-anchored-full-residual-arena4-v1",
        "work_order": WORK_ORDER, "baseline_sha": BASELINE_SHA,
        "classification": classification, "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "candidate_model_sha256": descriptor["candidate_model_sha256"],
        "training_config_hash": descriptor["training_config_hash"],
        "opening_corpus": opening_payload, "f78_first_two_pair_scores": F78_FIRST_TWO_PAIR_SCORES,
        "arena": arena,
        "contract_failures": failures,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in ("scripts/f79_parent_anchored_full_residual_arena4.py", "generic_chess/learning/arena.py", "generic_chess/learning/openings.py", "generic_chess/native/semantic_engine.py")
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    summary = result["arena"]["summary"] or {}
    print(json.dumps({
        "classification": result["classification"],
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "child_checkpoint_id": result["child_checkpoint_id"],
        "f78_first_two_pair_scores": result["f78_first_two_pair_scores"],
        "arena_pair_scores": summary.get("pair_scores"),
        "arena_mean_pair_score": summary.get("mean_pair_score"),
        "game_wins": summary.get("game_wins"), "game_draws": summary.get("game_draws"),
        "game_losses": summary.get("game_losses"),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
