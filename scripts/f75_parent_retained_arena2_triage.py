"""F75 two-pair strength triage for the accepted F74 candidate."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.arena import (  # noqa: E402
    ArenaConfig,
    ArenaExecutionCaps,
    run_arena_game_resumable,
)
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.learning.openings import (  # noqa: E402
    ArenaOpeningCorpus,
    generate_arena_openings,
)
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402


WORK_ORDER = "GENERICCHESS-F75-PARENT-RETAINED-ARENA2-STRENGTH-TRIAGE"
PARENT_SHA = "ec8167a056bac3206a39809abc4a13343c0a838c"
F74_SOURCE_SHA = PARENT_SHA
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
F74_CHILD_ID = "bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb"
F74_MODEL_SHA = "f29d7f7108c35e85ed66aa9b77f3bea8fcce1f7e4a51ede5f1923107f5b2ea69"
F74_RESULT = ROOT / ".generic_chess_flow" / "f74-parent-retained-output-delta-probe" / "f74_results.json"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
ARTIFACTS = ROOT / "artifacts" / "f75_parent_retained_arena"
CANDIDATE_PATH = ARTIFACTS / "candidate.json"
OPENINGS_PATH = ARTIFACTS / "openings.json"
OUT = ROOT / ".generic_chess_flow" / "f75-parent-retained-arena2-triage"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f75_results.json"
OPENING_SEED = 750501
OPENING_COUNT = 8
PAIRS = 2
NODES = 512
MAX_DEPTH = 12
TT_MEGABYTES = 8


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_gen1(compiled):
    data = json.loads((ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json").read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == "F60_D0_PAIRWISE_SEED_59012")
    gen1 = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F75 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _training_identity(raw_delta: list[float], alpha: float, parent_id: str) -> dict:
    return {
        "work_order": "GENERICCHESS-F74-PARENT-RETAINED-OUTPUT-DELTA-PROBE",
        "parent_checkpoint_id": parent_id,
        "fit_method": "deterministic_regularized_pairwise_output_delta",
        "fit_regularization": 0.001,
        "raw_delta": raw_delta,
        "alpha": alpha,
        "fitted_direction_norm": float(np.linalg.norm(np.asarray(raw_delta, dtype=np.float64))),
    }


def _candidate_from_descriptor(compiled):
    gen1 = _load_gen1(compiled)
    payload = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    required = {
        "schema", "source_commit", "parent_checkpoint_id", "child_checkpoint_id",
        "alpha", "raw_delta", "final_output_weights", "training_config_hash",
        "frozen_model_identity", "candidate_model_sha256",
    }
    if set(payload) != required:
        raise RuntimeError("F75 candidate descriptor fields are incomplete")
    if payload["parent_checkpoint_id"] != gen1.checkpoint_id:
        raise RuntimeError("F75 candidate descriptor parent mismatch")
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    if payload["frozen_model_identity"]["checkpoint_id"] != gen1.checkpoint_id:
        raise RuntimeError("F75 frozen model checkpoint identity mismatch")
    if payload["frozen_model_identity"]["compact_model_sha256"] != stable_sha256(parent_model.to_dict()):
        raise RuntimeError("F75 frozen model SHA mismatch")
    candidate_model = replace(
        parent_model,
        output_weights=tuple(float(value) for value in payload["final_output_weights"]),
    )
    if stable_sha256(candidate_model.to_dict()) != payload["candidate_model_sha256"]:
        raise RuntimeError("F75 candidate model SHA mismatch")
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=candidate_model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=payload["training_config_hash"],
        training_seed=None,
    )
    if candidate.checkpoint_id != payload["child_checkpoint_id"]:
        raise RuntimeError("F75 candidate checkpoint identity mismatch")
    if candidate.checkpoint_id != F74_CHILD_ID:
        raise RuntimeError("F75 candidate is not the accepted F74 child")
    candidate.validate_ruleset(compiled)
    return gen1, candidate, payload


def _materialize_candidate_descriptor(compiled) -> None:
    if CANDIDATE_PATH.is_file():
        return
    if not F74_RESULT.is_file():
        raise RuntimeError("F75 cannot bootstrap the durable candidate descriptor")
    gen1 = _load_gen1(compiled)
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    f74 = json.loads(F74_RESULT.read_text(encoding="utf-8"))
    delta = [float(value) for value in f74["correction"]["raw_delta"]]
    alpha = float(f74["correction"]["alpha_star"])
    final_weights = (np.asarray(parent_model.output_weights) + alpha * np.asarray(delta)).tolist()
    candidate_model = replace(parent_model, output_weights=tuple(final_weights))
    identity = _training_identity(delta, alpha, gen1.checkpoint_id)
    candidate = gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=candidate_model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=stable_sha256(identity),
        training_seed=None,
    )
    if candidate.checkpoint_id != F74_CHILD_ID:
        raise RuntimeError("F75 descriptor bootstrap does not reproduce F74 child")
    _atomic_json(CANDIDATE_PATH, {
        "schema": "generic-chess-f75-candidate-descriptor-v1",
        "source_commit": F74_SOURCE_SHA,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "alpha": alpha,
        "raw_delta": delta,
        "final_output_weights": final_weights,
        "training_config_hash": stable_sha256(identity),
        "frozen_model_identity": {
            "checkpoint_id": gen1.checkpoint_id,
            "compact_model_sha256": stable_sha256(parent_model.to_dict()),
            "width": parent_model.width,
            "perspective": parent_model.perspective,
        },
        "candidate_model_sha256": stable_sha256(candidate_model.to_dict()),
    })


def _f62_position_keys() -> set[str]:
    keys = set()
    for index in range(96):
        path = F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        keys.add(payload["identity"]["record"]["position_key"])
    return keys


def _load_or_make_openings(compiled) -> tuple[ArenaOpeningCorpus, dict]:
    if OPENINGS_PATH.is_file():
        payload = json.loads(OPENINGS_PATH.read_text(encoding="utf-8"))
        corpus = ArenaOpeningCorpus.from_dict(payload["corpus"])
        corpus.validate(compiled)
        if payload.get("corpus_id") != corpus.corpus_id:
            raise RuntimeError("F75 opening corpus SHA mismatch")
        if len(corpus.openings) != OPENING_COUNT or corpus.seed != OPENING_SEED:
            raise RuntimeError("F75 opening corpus configuration mismatch")
        return corpus, payload
    corpus = generate_arena_openings(
        compiled,
        count=OPENING_COUNT,
        seed=OPENING_SEED,
        min_plies=2,
        max_plies=6,
    )
    corpus.validate(compiled)
    keys = [opening.final_position_key for opening in corpus.openings]
    if len(set(keys)) != len(keys):
        raise RuntimeError("F75 opening final positions are not unique")
    overlap = sorted(set(keys) & _f62_position_keys())
    if overlap:
        raise RuntimeError("F75 opening corpus overlaps an F62 source root")
    payload = {
        "schema": "generic-chess-f75-opening-corpus-v1",
        "corpus": corpus.to_dict(),
        "corpus_id": corpus.corpus_id,
        "f62_source_records_sha256": "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61",
        "f62_overlap_count": len(overlap),
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
    rows = []
    for pair in summary.pairs:
        for game in (pair.game_child_owner0, pair.game_child_owner1):
            rows.extend(game.search_metrics)
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
        raise RuntimeError("F75 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    _materialize_candidate_descriptor(compiled)
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
        stage_id="f75-arena2",
    )
    replay = run_arena_game_resumable(
        compiled, native, gen1, candidate, config,
        progress_dir=PROGRESS,
        openings=openings,
        capture_search_metrics=True,
        caps=caps,
        stage_id="f75-arena2",
    )
    contract_failures = []
    if first.status != "COMPLETE" or first.completed_games != 2 * PAIRS:
        contract_failures.append("stage did not complete all four games")
    if first.summary is None:
        contract_failures.append("complete stage has no pair summary")
    if replay.status != first.status or replay.completed_games != first.completed_games:
        contract_failures.append("progress replay status differs")
    if _summary_payload(first.summary) != _summary_payload(replay.summary):
        contract_failures.append("progress replay summary differs")
    telemetry = _telemetry(first.summary) if first.summary is not None else {}
    if not telemetry.get("all_root_window_pruning_true", False):
        contract_failures.append("root pruning telemetry was not true for every search")
    if telemetry.get("missing_root_window_pruning_rows", 0):
        contract_failures.append("root pruning telemetry field was missing")
    if first.reason is not None:
        contract_failures.append(f"execution cap or stop reason: {first.reason}")
    if first.summary is not None and not contract_failures:
        classification = (
            "PARENT_RETAINED_ARENA2_SURVIVES"
            if first.summary.mean_pair_score >= 0.5
            else "PARENT_RETAINED_ARENA2_REJECTED"
        )
    elif first.status != "COMPLETE":
        classification = "PARENT_RETAINED_ARENA2_UNRESOLVED"
    else:
        classification = "HARNESS_MISMATCH"
    result = {
        "schema": "generic-chess-f75-parent-retained-arena2-triage-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "candidate_descriptor": {
            "path": str(CANDIDATE_PATH.relative_to(ROOT)),
            "source_commit": descriptor["source_commit"],
            "alpha": descriptor["alpha"],
            "candidate_model_sha256": descriptor["candidate_model_sha256"],
        },
        "opening_corpus": {
            "path": str(OPENINGS_PATH.relative_to(ROOT)),
            "corpus_id": opening_payload["corpus_id"],
            "seed": OPENING_SEED,
            "opening_count": OPENING_COUNT,
            "f62_overlap_count": opening_payload.get("f62_overlap_count", 0),
            "unique_final_position_count": opening_payload.get("unique_final_position_count", OPENING_COUNT),
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
        "summary": _summary_payload(first.summary),
        "telemetry": telemetry,
        "replay_validation": {
            "status": replay.status,
            "completed_games": replay.completed_games,
            "completed_pairs": replay.completed_pairs,
            "summary_equal": _summary_payload(first.summary) == _summary_payload(replay.summary),
        },
        "contract_failures": contract_failures,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                "scripts/f75_parent_retained_arena2_triage.py",
                "generic_chess/learning/arena.py",
                "generic_chess/native/semantic_engine.py",
                "generic_chess/learning/openings.py",
            )
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "mean_pair_score": None if result["summary"] is None else result["summary"]["mean_pair_score"],
        "game_wins": None if result["summary"] is None else result["summary"]["game_wins"],
        "game_draws": None if result["summary"] is None else result["summary"]["game_draws"],
        "game_losses": None if result["summary"] is None else result["summary"]["game_losses"],
        "completed_games": result["run"]["completed_games"],
        "root_pruning_telemetry": result["telemetry"].get("all_root_window_pruning_true"),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
