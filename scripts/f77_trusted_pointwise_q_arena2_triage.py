"""F77 two-pair Arena2 triage for the durable F76-R2 candidate."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import ArenaConfig, ArenaExecutionCaps, run_arena_game_resumable  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f75_parent_retained_arena2_triage as f75  # noqa: E402


WORK_ORDER = "GENERICCHESS-F77-TRUSTED-POINTWISE-Q-ARENA2-STRENGTH-TRIAGE"
PARENT_SHA = "2eac3d2ac36519dfaab2b2cd6a6112d9404b5c00"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
R2_ID = "fb3d3113b7044de6ebbf17352d7e34f0713618afbaae6eb792ebb515b09f30db"
R2_DESCRIPTOR = ROOT / "artifacts" / "f76_r2_trusted_pointwise_q" / "candidate.json"
F75_OPENINGS = ROOT / "artifacts" / "f75_parent_retained_arena" / "openings.json"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
ARTIFACTS = ROOT / "artifacts" / "f77_trusted_pointwise_q_arena"
OPENINGS_PATH = ARTIFACTS / "openings.json"
OUT = ROOT / ".generic_chess_flow" / "f77-trusted-pointwise-q-arena2"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f77_results.json"
OPENING_SEED = 770501
OPENING_COUNT = 8
PAIRS = 2
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_gen1(compiled):
    data = json.loads((ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json").read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012")
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F77 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _candidate_from_descriptor(compiled):
    gen1 = _load_gen1(compiled)
    payload = json.loads(R2_DESCRIPTOR.read_text(encoding="utf-8"))
    identity = payload["canonical_training_identity"]
    if stable_sha256(identity) != payload["canonical_training_config_hash"]:
        raise RuntimeError("F77 R2 canonical training hash mismatch")
    model = replace(
        CompactNonlinearResidual.from_dict(gen1.compact_nonlinear),
        output_weights=tuple(float(value) for value in payload["final_output_weights"]),
    )
    if stable_sha256(model.to_dict()) != payload["candidate_model_sha256"]:
        raise RuntimeError("F77 R2 evaluator model SHA mismatch")
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=payload["canonical_training_config_hash"],
        training_seed=None,
    )
    if candidate.checkpoint_id != R2_ID or payload["child_checkpoint_id"] != R2_ID:
        raise RuntimeError("F77 R2 checkpoint identity mismatch")
    candidate.validate_ruleset(compiled)
    return gen1, candidate, payload


def _f62_position_keys() -> set[str]:
    return {
        json.loads((F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json").read_text(encoding="utf-8"))["identity"]["record"]["position_key"]
        for index in range(96)
    }


def _load_or_make_openings(compiled):
    if OPENINGS_PATH.is_file():
        payload = json.loads(OPENINGS_PATH.read_text(encoding="utf-8"))
        corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
        corpus.validate(compiled)
        if payload.get("corpus_id") != corpus.corpus_id:
            raise RuntimeError("F77 opening corpus SHA mismatch")
        return corpus, payload
    corpus = generate_arena_openings(compiled, count=OPENING_COUNT, seed=OPENING_SEED, min_plies=2, max_plies=6)
    corpus.validate(compiled)
    keys = [opening.final_position_key for opening in corpus.openings]
    f62_overlap = sorted(set(keys) & _f62_position_keys())
    f75_payload = json.loads(F75_OPENINGS.read_text(encoding="utf-8"))
    f75_keys = {opening["final_position_key"] for opening in f75_payload["corpus"]["openings"]}
    f75_overlap = sorted(set(keys) & f75_keys)
    if len(set(keys)) != OPENING_COUNT or f62_overlap or f75_overlap:
        raise RuntimeError("F77 opening corpus uniqueness or overlap contract failed")
    payload = {
        "schema": "generic-chess-f77-trusted-pointwise-q-opening-corpus-v1",
        "corpus": corpus.to_dict(),
        "corpus_id": corpus.corpus_id,
        "f62_overlap_count": len(f62_overlap),
        "f75_overlap_count": len(f75_overlap),
        "unique_final_position_count": len(set(keys)),
    }
    _atomic_json(OPENINGS_PATH, payload)
    return corpus, payload


def _game_payload(game) -> dict:
    return {
        "pair": game.pair,
        "child_owner": game.child_owner,
        "winner": game.winner,
        "result": game.result,
        "plies": game.plies,
        "opening_id": game.opening_id,
        "opening_position_key": game.opening_position_key,
        "final_position_key": game.final_position_key,
        "search_metrics": list(game.search_metrics),
    }


def _summary_payload(summary) -> dict | None:
    if summary is None:
        return None
    return {
        "pair_count": summary.pair_count,
        "pair_scores": list(summary.pair_scores),
        "mean_pair_score": summary.mean_pair_score,
        "child_better_pairs": summary.child_better_pairs,
        "tied_pairs": summary.tied_pairs,
        "child_worse_pairs": summary.child_worse_pairs,
        "bootstrap_low": summary.bootstrap_low,
        "bootstrap_high": summary.bootstrap_high,
        "game_wins": summary.game_wins,
        "game_draws": summary.game_draws,
        "game_losses": summary.game_losses,
        "game_score_rate": summary.game_score_rate,
        "pairs": [
            {
                "pair_index": pair.pair_index,
                "opening_id": pair.opening_id,
                "game_child_owner0": _game_payload(pair.game_child_owner0),
                "game_child_owner1": _game_payload(pair.game_child_owner1),
            }
            for pair in summary.pairs
        ],
    }


def _telemetry(summary) -> dict:
    games = [game for pair in summary.pairs for game in (pair.game_child_owner0, pair.game_child_owner1)]
    rows = [metric for game in games for metric in game.search_metrics]
    by_role = {}
    for role in ("parent", "child"):
        selected = [row for row in rows if row.get("engine_role") == role]
        by_role[role] = {
            "searches": len(selected),
            "nodes": sum(int(row["nodes"]) for row in selected),
            "completed_depths": {
                str(depth): sum(int(row["completed_depth"]) == depth for row in selected)
                for depth in sorted({int(row["completed_depth"]) for row in selected})
            },
            "termination_reasons": sorted({str(row["termination_reason"]) for row in selected}),
        }
    return {
        "total_searches": len(rows),
        "by_role": by_role,
        "all_root_window_pruning_true": all(row.get("root_window_pruning") is True for row in rows),
        "missing_root_window_pruning_rows": sum("root_window_pruning" not in row for row in rows),
        "max_nodes_per_search": max((int(row["nodes"]) for row in rows), default=0),
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F77 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1, candidate, descriptor = _candidate_from_descriptor(compiled)
    openings, opening_payload = _load_or_make_openings(compiled)
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
        max_stage_games=4,
        max_concurrent_games=4,
        stage_wall_seconds=3600,
    )
    first = run_arena_game_resumable(
        compiled, native, gen1, candidate, config,
        progress_dir=PROGRESS,
        openings=openings,
        capture_search_metrics=True,
        caps=caps,
        stage_id="f77-arena2",
    )
    replay = run_arena_game_resumable(
        compiled, native, gen1, candidate, config,
        progress_dir=PROGRESS,
        openings=openings,
        capture_search_metrics=True,
        caps=caps,
        stage_id="f77-arena2",
    )
    summary = _summary_payload(first.summary)
    replay_summary = _summary_payload(replay.summary)
    contract_failures = []
    if first.status != "COMPLETE" or first.completed_games != 2 * PAIRS or first.completed_pairs != PAIRS:
        contract_failures.append("stage did not complete all four games and two pairs")
    if summary is None:
        contract_failures.append("complete stage has no pair summary")
    if replay.status != first.status or replay.completed_games != first.completed_games or replay.completed_pairs != first.completed_pairs:
        contract_failures.append("progress replay status or counts differ")
    if summary != replay_summary:
        contract_failures.append("progress replay summary differs")
    telemetry = _telemetry(first.summary) if first.summary is not None else {}
    if telemetry and not telemetry.get("all_root_window_pruning_true", False):
        contract_failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        contract_failures.append("root pruning telemetry field was missing")
    if first.reason is not None:
        contract_failures.append(f"execution cap or stop reason: {first.reason}")
    if contract_failures:
        classification = "HARNESS_MISMATCH" if first.status == "COMPLETE" else "TRUSTED_POINTWISE_Q_ARENA2_UNRESOLVED"
    elif first.status != "COMPLETE":
        classification = "TRUSTED_POINTWISE_Q_ARENA2_UNRESOLVED"
    elif first.summary.mean_pair_score >= 0.5:
        classification = "TRUSTED_POINTWISE_Q_ARENA2_SURVIVES"
    else:
        classification = "TRUSTED_POINTWISE_Q_ARENA2_REJECTED"
    result = {
        "schema": "generic-chess-f77-trusted-pointwise-q-arena2-triage-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "candidate_descriptor": {
            "path": str(R2_DESCRIPTOR.relative_to(ROOT)),
            "canonical_training_config_hash": descriptor["canonical_training_config_hash"],
            "candidate_model_sha256": descriptor["candidate_model_sha256"],
        },
        "opening_corpus": {
            "path": str(OPENINGS_PATH.relative_to(ROOT)),
            "corpus_id": opening_payload["corpus_id"],
            "seed": OPENING_SEED,
            "opening_count": OPENING_COUNT,
            "f62_overlap_count": opening_payload["f62_overlap_count"],
            "f75_overlap_count": opening_payload["f75_overlap_count"],
            "unique_final_position_count": opening_payload["unique_final_position_count"],
        },
        "config": {
            "pairs": PAIRS,
            "total_games": 2 * PAIRS,
            "nodes_per_move": NODES,
            "parent_nodes_per_move": NODES,
            "child_nodes_per_move": NODES,
            "max_depth": MAX_DEPTH,
            "tt_megabytes": TT_MEGABYTES,
            "workers": 1,
            "root_window_pruning": True,
            "execution_caps": asdict(caps),
        },
        "run": {
            "status": first.status,
            "completed_games": first.completed_games,
            "completed_pairs": first.completed_pairs,
            "total_games": first.total_games,
            "reason": first.reason,
            "effective_game_lanes": first.effective_game_lanes,
        },
        "summary": summary,
        "telemetry": telemetry,
        "replay_validation": {
            "status": replay.status,
            "completed_games": replay.completed_games,
            "completed_pairs": replay.completed_pairs,
            "summary_equal": summary == replay_summary,
        },
        "contract_failures": contract_failures,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                "scripts/f77_trusted_pointwise_q_arena2_triage.py",
                "generic_chess/learning/arena.py",
                "generic_chess/learning/openings.py",
                "generic_chess/native/semantic_engine.py",
            )
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    summary = result["summary"] or {}
    print(json.dumps({
        "classification": result["classification"],
        "parent_checkpoint_id": result["parent_checkpoint_id"],
        "child_checkpoint_id": result["child_checkpoint_id"],
        "opening_corpus_id": result["opening_corpus"]["corpus_id"],
        "pair_scores": summary.get("pair_scores"),
        "mean_pair_score": summary.get("mean_pair_score"),
        "game_wins": summary.get("game_wins"),
        "game_draws": summary.get("game_draws"),
        "game_losses": summary.get("game_losses"),
        "completed_games": result["run"]["completed_games"],
        "root_pruning_telemetry": result["telemetry"].get("all_root_window_pruning_true"),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
